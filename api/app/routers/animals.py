from datetime import date, datetime
from typing import List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session

from sqlalchemy.orm import selectinload

from ..db import get_db
from ..models import Animal, Group, Farm, Role, Scan, User, UserFarm, UserRole
from ..s3_utils import generate_presigned_url
from .me import get_current_user

router = APIRouter()

ALLOWED_ROLES: Set[str] = {"admin", "technician", "farmer"}


class AnimalOut(BaseModel):
    id: UUID
    tag_id: str
    rfid: Optional[str]
    breed: Optional[str]
    sex: Optional[str]
    birth_date: Optional[date]
    farm_id: Optional[UUID]
    farm_name: Optional[str]
    group_id: Optional[UUID]
    group_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AnimalScanOut(BaseModel):
    id: UUID
    capture_id: str
    label: Optional[str]
    created_at: datetime
    grading: Optional[str]
    latest_model: Optional[str]
    latest_version: Optional[str]
    latest_confidence: Optional[float]
    imf: Optional[float]
    backfat_thickness: Optional[float]
    animal_weight: Optional[float]
    ribeye_area: Optional[float]
    image_url: Optional[str]
    image_key: Optional[str]


class AnimalCreate(BaseModel):
    tag_id: constr(strip_whitespace=True, min_length=1, max_length=255)
    rfid: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    breed: Optional[str] = None
    sex: Optional[str] = None
    birth_date: Optional[date] = None
    farm_id: Optional[UUID] = None
    group_id: Optional[UUID] = None


class AnimalUpdate(BaseModel):
    tag_id: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    rfid: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    breed: Optional[str] = None
    sex: Optional[str] = None
    birth_date: Optional[date] = None
    farm_id: Optional[UUID] = None
    group_id: Optional[UUID] = None


def get_role_names(db: Session, user: User) -> Set[str]:
    rows = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    return {name for (name,) in rows}


def get_accessible_farm_ids(db: Session, user: User) -> Set[UUID]:
    rows = (
        db.query(UserFarm.farm_id)
        .filter(UserFarm.user_id == user.id)
        .all()
    )
    return {row[0] for row in rows}


def ensure_farm_permission(
    *,
    farm_id: Optional[UUID],
    role_names: Set[str],
    accessible_farms: Set[UUID],
) -> None:
    if farm_id is None:
        if "admin" not in role_names:
            raise HTTPException(status_code=403, detail="Farm selection required")
        return
    if "admin" in role_names:
        return
    if farm_id not in accessible_farms:
        raise HTTPException(status_code=403, detail="You cannot manage this farm")


def serialize_animal(instance: Animal) -> AnimalOut:
    return AnimalOut(
        id=instance.id,
        tag_id=instance.tag_id,
        rfid=instance.rfid,
        breed=instance.breed,
        sex=instance.sex,
        birth_date=instance.birth_date,
        farm_id=instance.farm_id,
        farm_name=instance.farm.name if instance.farm else None,
        group_id=instance.group_id,
        group_name=instance.group.name if instance.group else None,
        created_at=instance.created_at,
    )


def serialize_animal_scan(scan: Scan) -> AnimalScanOut:
    latest = None
    if scan.grading_results:
        latest = sorted(scan.grading_results, key=lambda g: g.created_at, reverse=True)[0]
    image_url = None
    if scan.image_asset:
        image_url = generate_presigned_url(scan.image_asset.bucket, scan.image_asset.object_key)
    return AnimalScanOut(
        id=scan.id,
        capture_id=scan.capture_id,
        label=scan.label,
        created_at=scan.created_at,
        grading=scan.grading,
        latest_model=latest.model_name if latest else None,
        latest_version=latest.model_version if latest else None,
        latest_confidence=float(latest.confidence) if latest and latest.confidence is not None else None,
        imf=float(scan.imf) if scan.imf is not None else None,
        backfat_thickness=float(scan.backfat_thickness) if scan.backfat_thickness is not None else None,
        animal_weight=float(scan.animal_weight) if scan.animal_weight is not None else None,
        ribeye_area=float(scan.ribeye_area) if scan.ribeye_area is not None else None,
        image_url=image_url,
        image_key=scan.image_asset.object_key if scan.image_asset else None,
    )


@router.get("", response_model=List[AnimalOut])
def list_animals(
    farm_id: Optional[UUID] = None,
    group_id: Optional[UUID] = None,
    tag: Optional[str] = None,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(Animal).outerjoin(Farm).outerjoin(Group)
    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        query = query.filter(
            (Animal.farm_id == None) | (Animal.farm_id.in_(accessible_farms))  # noqa: E711
        )
    if farm_id:
        query = query.filter(Animal.farm_id == farm_id)
    if group_id:
        query = query.filter(Animal.group_id == group_id)
    if tag:
        like = f"%{tag}%"
        query = query.filter(Animal.tag_id.ilike(like))
    animals = query.order_by(Animal.created_at.desc()).all()
    return [serialize_animal(animal) for animal in animals]


@router.post("", response_model=AnimalOut)
def create_animal(
    payload: AnimalCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    accessible_farms = get_accessible_farm_ids(db, current)
    ensure_farm_permission(
        farm_id=payload.farm_id,
        role_names=role_names,
        accessible_farms=accessible_farms,
    )

    if payload.rfid:
        existing = db.query(Animal).filter(Animal.rfid == payload.rfid).first()
        if existing:
            raise HTTPException(status_code=400, detail="Animal RFID already exists")

    animal = Animal(
        tag_id=payload.tag_id,
        rfid=payload.rfid,
        breed=payload.breed,
        sex=payload.sex,
        birth_date=payload.birth_date,
        farm_id=payload.farm_id,
        group_id=payload.group_id,
    )
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return serialize_animal(animal)


@router.get("/{animal_id}", response_model=AnimalOut)
def get_animal(
    animal_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        if animal.farm_id and animal.farm_id not in accessible_farms:
            raise HTTPException(status_code=403, detail="Not authorized to view this animal")

    return serialize_animal(animal)


@router.get("/{animal_id}/scans", response_model=List[AnimalScanOut])
def get_animal_scans(
    animal_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        if animal.farm_id and animal.farm_id not in accessible_farms:
            raise HTTPException(status_code=403, detail="Not authorized to view this animal")

    scans = (
        db.query(Scan)
        .options(
            selectinload(Scan.grading_results),
            selectinload(Scan.image_asset),
        )
        .filter(Scan.animal_id == animal.id)
        .order_by(Scan.created_at.desc())
        .all()
    )
    return [serialize_animal_scan(scan) for scan in scans]


@router.put("/{animal_id}", response_model=AnimalOut)
def update_animal(
    animal_id: UUID,
    payload: AnimalUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    accessible_farms = get_accessible_farm_ids(db, current)
    farm_candidate = payload.farm_id if payload.farm_id is not None else animal.farm_id
    ensure_farm_permission(
        farm_id=farm_candidate,
        role_names=role_names,
        accessible_farms=accessible_farms,
    )

    if payload.rfid and payload.rfid != animal.rfid:
        existing = db.query(Animal).filter(Animal.rfid == payload.rfid).first()
        if existing:
            raise HTTPException(status_code=400, detail="Animal RFID already exists")

    if payload.tag_id is not None:
        animal.tag_id = payload.tag_id
    if payload.rfid is not None:
        animal.rfid = payload.rfid
    if payload.breed is not None:
        animal.breed = payload.breed
    if payload.sex is not None:
        animal.sex = payload.sex
    if payload.birth_date is not None:
        animal.birth_date = payload.birth_date
    animal.farm_id = farm_candidate
    if payload.group_id is not None:
        animal.group_id = payload.group_id

    db.commit()
    db.refresh(animal)
    return serialize_animal(animal)


@router.delete("/{animal_id}", status_code=204)
def delete_animal(
    animal_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    animal = db.get(Animal, animal_id)
    if not animal:
        raise HTTPException(status_code=404, detail="Animal not found")

    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        if animal.farm_id and animal.farm_id not in accessible_farms:
            raise HTTPException(status_code=403, detail="Not authorized to delete this animal")

    db.delete(animal)
    db.commit()
