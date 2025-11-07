from datetime import date, datetime
from typing import List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Cattle, Farm, Role, User, UserFarm, UserRole
from .me import get_current_user

router = APIRouter()

ALLOWED_ROLES: Set[str] = {"admin", "technician", "farmer"}


class CattleOut(BaseModel):
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


class CattleCreate(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    external_id: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    born_date: Optional[date] = None
    farm_id: Optional[UUID] = None


class CattleUpdate(BaseModel):
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


def serialize_cattle(instance: Cattle) -> CattleOut:
    return CattleOut(
        id=instance.id,
        name=instance.name,
        external_id=instance.external_id,
        born_date=instance.born_date,
        farm_id=instance.farm_id,
        farm_name=instance.farm.name if instance.farm else None,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


@router.get("", response_model=List[CattleOut])
def list_cattle(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = db.query(Cattle).outerjoin(Farm)
    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        query = query.filter(
            (Cattle.farm_id == None) | (Cattle.farm_id.in_(accessible_farms))  # noqa: E711
        )
    cattle = query.order_by(Cattle.created_at.desc()).all()
    return [serialize_cattle(c) for c in cattle]


@router.post("", response_model=CattleOut)
def create_cattle(
    payload: CattleCreate,
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
            db.query(Cattle)
            .filter(Cattle.external_id == payload.external_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="External cattle ID already exists")

    cattle = Cattle(
        name=payload.name,
        external_id=payload.external_id,
        born_date=payload.born_date,
        farm_id=payload.farm_id,
    )
    db.add(cattle)
    db.commit()
    db.refresh(cattle)
    return serialize_cattle(cattle)


@router.get("/{cattle_id}", response_model=CattleOut)
def get_cattle(
    cattle_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    cattle = db.get(Cattle, cattle_id)
    if not cattle:
        raise HTTPException(status_code=404, detail="Cattle not found")

    if "admin" not in role_names:
        accessible_farms = get_accessible_farm_ids(db, current)
        if cattle.farm_id and cattle.farm_id not in accessible_farms:
            raise HTTPException(status_code=403, detail="Not authorized to view this cattle")

    return serialize_cattle(cattle)


@router.put("/{cattle_id}", response_model=CattleOut)
def update_cattle(
    cattle_id: UUID,
    payload: CattleUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    cattle = db.get(Cattle, cattle_id)
    if not cattle:
        raise HTTPException(status_code=404, detail="Cattle not found")

    accessible_farms = get_accessible_farm_ids(db, current)
    if "admin" not in role_names:
        if cattle.farm_id and cattle.farm_id not in accessible_farms:
            raise HTTPException(status_code=403, detail="Not authorized to modify this cattle")

    new_farm_id = payload.farm_id if payload.farm_id is not None else cattle.farm_id
    ensure_farm_access(
        farm_id=new_farm_id,
        role_names=role_names,
        accessible_farms=accessible_farms,
    )

    if payload.external_id and payload.external_id != cattle.external_id:
        existing = (
            db.query(Cattle)
            .filter(Cattle.external_id == payload.external_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="External cattle ID already exists")

    if payload.name is not None:
        cattle.name = payload.name
    if payload.external_id is not None:
        cattle.external_id = payload.external_id
    if payload.born_date is not None:
        cattle.born_date = payload.born_date
    cattle.farm_id = new_farm_id

    db.commit()
    db.refresh(cattle)
    return serialize_cattle(cattle)
