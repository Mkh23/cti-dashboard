from datetime import datetime
from typing import List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Farm, Role, User, UserFarm, UserRole
from .me import get_current_user

router = APIRouter()

ALLOWED_ROLES: Set[str] = {"admin", "technician", "farmer"}


def get_role_names(db: Session, user: User) -> Set[str]:
    roles = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    return {name for (name,) in roles}


class FarmOwnerOut(BaseModel):
    user_id: UUID
    email: str
    full_name: Optional[str]


class FarmOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    owners: List[FarmOwnerOut]
    can_edit: bool


class FarmCreate(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    owner_ids: Optional[List[UUID]] = None


class FarmUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    owner_ids: Optional[List[UUID]] = None


def serialize_farm(farm: Farm, current_user: User, role_names: Set[str]) -> FarmOut:
    owners = [
        FarmOwnerOut(
            user_id=link.user_id,
            email=link.user.email,
            full_name=link.user.full_name,
        )
        for link in farm.user_links
        if link.is_owner
    ]
    can_edit = "admin" in role_names or any(
        link.user_id == current_user.id and link.is_owner for link in farm.user_links
    )
    return FarmOut(
        id=farm.id,
        name=farm.name,
        created_at=farm.created_at,
        updated_at=farm.updated_at,
        owners=owners,
        can_edit=can_edit,
    )


def base_query(db: Session):
    return db.query(Farm).options(
        selectinload(Farm.user_links).selectinload(UserFarm.user)
    )


def ensure_owner_ids(
    db: Session, owner_ids: Set[UUID], *, allow_empty: bool = False
) -> Set[UUID]:
    if not owner_ids and not allow_empty:
        raise HTTPException(status_code=400, detail="At least one owner is required")

    if not owner_ids:
        return owner_ids

    users = db.query(User.id).filter(User.id.in_(owner_ids)).all()
    found = {row[0] for row in users}
    missing = owner_ids - found
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown owner ids: {', '.join(sorted(str(mid) for mid in missing))}",
        )
    return owner_ids


@router.get("", response_model=List[FarmOut])
def list_farms(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = base_query(db).order_by(Farm.name)
    if "admin" in role_names:
        farms = query.all()
    else:
        farms = (
            query.join(UserFarm, UserFarm.farm_id == Farm.id)
            .filter(UserFarm.user_id == current.id)
            .all()
        )
    return [serialize_farm(farm, current, role_names) for farm in farms]


@router.post("", response_model=FarmOut)
def create_farm(
    payload: FarmCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    owner_ids = set(payload.owner_ids or [])
    if "admin" not in role_names:
        owner_ids = owner_ids | {current.id}
        if owner_ids != {current.id}:
            raise HTTPException(
                status_code=403,
                detail="You can only assign yourself as the owner of a farm",
            )

    if not owner_ids:
        owner_ids = {current.id}

    ensure_owner_ids(db, owner_ids)

    farm = Farm(name=payload.name)
    db.add(farm)
    db.flush()

    farm_id = farm.id

    for owner_id in owner_ids:
        db.add(UserFarm(user_id=owner_id, farm_id=farm_id, is_owner=True))

    db.commit()

    farm = base_query(db).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=500, detail="Failed to create farm")
    return serialize_farm(farm, current, role_names)


def require_farm_access(
    db: Session, current: User, farm_id: UUID, role_names: Set[str]
) -> Farm:
    farm = (
        base_query(db)
        .filter(Farm.id == farm_id)
        .first()
    )
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    if "admin" in role_names:
        return farm

    has_access = any(
        link.user_id == current.id and link.is_owner for link in farm.user_links
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Not authorized to access this farm")
    return farm


@router.get("/{farm_id}", response_model=FarmOut)
def get_farm(
    farm_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    farm = require_farm_access(db, current, farm_id, role_names)
    return serialize_farm(farm, current, role_names)


@router.put("/{farm_id}", response_model=FarmOut)
def update_farm(
    farm_id: UUID,
    payload: FarmUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    farm = require_farm_access(db, current, farm_id, role_names)

    if payload.name is not None:
        farm.name = payload.name

    if payload.owner_ids is not None:
        new_owner_ids = set(payload.owner_ids)
        if "admin" not in role_names:
            if new_owner_ids != {current.id}:
                raise HTTPException(
                    status_code=403,
                    detail="You can only manage yourself as an owner",
                )
        else:
            ensure_owner_ids(db, new_owner_ids)
        if not new_owner_ids:
            raise HTTPException(status_code=400, detail="At least one owner is required")

        db.query(UserFarm).filter(UserFarm.farm_id == farm.id).delete()
        for owner_id in new_owner_ids:
            db.add(UserFarm(user_id=owner_id, farm_id=farm.id, is_owner=True))

    db.commit()

    farm = require_farm_access(db, current, farm_id, role_names)
    return serialize_farm(farm, current, role_names)
