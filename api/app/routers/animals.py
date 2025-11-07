from datetime import date, datetime
from typing import List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Animal, Cattle, Farm, Role, User, UserFarm, UserRole
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
    cattle_id: Optional[UUID]
    cattle_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AnimalCreate(BaseModel):
    tag_id: constr(strip_whitespace=True, min_length=1, max_length=255)
    rfid: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    breed: Optional[str] = None
    sex: Optional[str] = None
    birth_date: Optional[date] = None
    farm_id: Optional[UUID] = None
    cattle_id: Optional[UUID] = None


class AnimalUpdate(BaseModel):
    tag_id: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    rfid: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    breed: Optional[str] = None
    sex: Optional[str] = None
    birth_date: Optional[date] = None
    farm_id: Optional[UUID] = None
    cattle_id: Optional[UUID] = None


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
        cattle_id=instance.cattle_id,
        cattle_name=instance.cattle.name if instance.cattle else None,
        created_at=instance.created_at,
    )


@router.get("", response_model=List[AnimalOut])
def list_animals(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(Animal).outerjoin(Farm).outerjoin(Cattle)
    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        query = query.filter(
            (Animal.farm_id == None) | (Animal.farm_id.in_(accessible_farms))  # noqa: E711
        )
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
        cattle_id=payload.cattle_id,
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
    if payload.cattle_id is not None:
        animal.cattle_id = payload.cattle_id

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
