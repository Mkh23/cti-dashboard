from datetime import date, datetime
from typing import List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Animal, Group, Farm, Role, Scan, User, UserFarm, UserRole
from .animals import serialize_animal, AnimalOut
from .me import get_current_user

router = APIRouter()

ALLOWED_ROLES: Set[str] = {"admin", "technician", "farmer"}


class GroupOut(BaseModel):
    id: UUID
    name: str
    external_id: Optional[str]
    born_date: Optional[date]
    farm_id: Optional[UUID]
    farm_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GroupCreate(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    external_id: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    born_date: Optional[date] = None
    farm_id: Optional[UUID] = None


class GroupUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    external_id: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    born_date: Optional[date] = None
    farm_id: Optional[UUID] = None


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


def ensure_farm_access(
    *,
    farm_id: Optional[UUID],
    role_names: Set[str],
    accessible_farms: Set[UUID],
) -> None:
    if farm_id is None:
        if "admin" not in role_names:
            raise HTTPException(status_code=403, detail="Farm selection is required for your role")
        return

    if "admin" in role_names:
        return
    if farm_id not in accessible_farms:
        raise HTTPException(status_code=403, detail="You are not permitted to manage this farm")


def serialize_group(instance: Group) -> GroupOut:
    return GroupOut(
        id=instance.id,
        name=instance.name,
        external_id=instance.external_id,
        born_date=instance.born_date,
        farm_id=instance.farm_id,
        farm_name=instance.farm.name if instance.farm else None,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.get("", response_model=List[GroupOut])
def list_groups(
    farm_id: Optional[UUID] = None,
    born_from: Optional[date] = None,
    born_to: Optional[date] = None,
    name: Optional[str] = None,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(Group).outerjoin(Farm)
    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        query = query.filter(
            (Group.farm_id == None) | (Group.farm_id.in_(accessible_farms))  # noqa: E711
        )
    if farm_id:
        query = query.filter(Group.farm_id == farm_id)
    if born_from:
        query = query.filter(Group.born_date >= born_from)
    if born_to:
        query = query.filter(Group.born_date <= born_to)
    if name:
        query = query.filter(Group.name.ilike(f"%{name}%"))
    group = query.order_by(Group.created_at.desc()).all()
    return [serialize_group(c) for c in group]


@router.get("/{group_id}/animals", response_model=List[AnimalOut])
def group_animals(
    group_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    group = (
        db.query(Group)
        .options(selectinload(Group.animals).selectinload(Animal.farm))
        .filter(Group.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        if group.farm_id and group.farm_id not in accessible_farms:
            raise HTTPException(status_code=403, detail="Not authorized to view this group")
        animals = [a for a in group.animals if (a.farm_id in accessible_farms) or a.farm_id is None]
    else:
        animals = group.animals

    return [serialize_animal(animal) for animal in animals]


@router.post("", response_model=GroupOut)
def create_group(
    payload: GroupCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    accessible_farms = get_accessible_farm_ids(db, current)
    ensure_farm_access(
        farm_id=payload.farm_id,
        role_names=role_names,
        accessible_farms=accessible_farms,
    )

    if payload.external_id:
        existing = (
            db.query(Group)
            .filter(Group.external_id == payload.external_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="External group ID already exists")

    group = Group(
        name=payload.name,
        external_id=payload.external_id,
        born_date=payload.born_date,
        farm_id=payload.farm_id,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return serialize_group(group)


@router.get("/{group_id}", response_model=GroupOut)
def get_group(
    group_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        if group.farm_id and group.farm_id not in accessible_farms:
            raise HTTPException(status_code=403, detail="Not authorized to view this group")

    return serialize_group(group)


@router.put("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    accessible_farms = get_accessible_farm_ids(db, current)
    if "admin" not in role_names:
        if group.farm_id and group.farm_id not in accessible_farms:
            raise HTTPException(status_code=403, detail="Not authorized to modify this group")

    new_farm_id = payload.farm_id if payload.farm_id is not None else group.farm_id
    ensure_farm_access(
        farm_id=new_farm_id,
        role_names=role_names,
        accessible_farms=accessible_farms,
    )

    if payload.external_id and payload.external_id != group.external_id:
        existing = (
            db.query(Group)
            .filter(Group.external_id == payload.external_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="External group ID already exists")

    old_farm_id = group.farm_id
    old_born_date = group.born_date
    if payload.name is not None:
        group.name = payload.name
    if payload.external_id is not None:
        group.external_id = payload.external_id
    if payload.born_date is not None:
        group.born_date = payload.born_date
    group.farm_id = new_farm_id

    # Cascade farm assignment and born_date to related animals and scans when group changes
    if new_farm_id != old_farm_id or group.born_date != old_born_date:
        new_farm = db.query(Farm).filter(Farm.id == new_farm_id).first() if new_farm_id else None
        animals = db.query(Animal).filter(Animal.group_id == group.id).all()
        animal_ids = [a.id for a in animals]
        for animal in animals:
            if new_farm_id != old_farm_id:
                animal.farm_id = new_farm_id
                animal.farm = new_farm
            if group.born_date != old_born_date:
                animal.birth_date = group.born_date

        if animal_ids:
            updates = {}
            if new_farm_id != old_farm_id:
                updates["farm_id"] = new_farm_id
            if updates:
                (
                    db.query(Scan)
                    .filter((Scan.animal_id.in_(animal_ids)) | (Scan.group_id == group.id))
                    .update(updates, synchronize_session=False)
                )

    db.commit()
    db.refresh(group)
    return serialize_group(group)
