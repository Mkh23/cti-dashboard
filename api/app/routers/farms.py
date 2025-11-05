from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, constr, root_validator
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


def fetch_roles_for_users(db: Session, user_ids: Set[UUID]) -> Dict[UUID, List[str]]:
    if not user_ids:
        return {}

    rows = (
        db.query(UserRole.user_id, Role.name)
        .join(Role, Role.id == UserRole.role_id)
        .filter(UserRole.user_id.in_(user_ids))
        .all()
    )
    role_map: Dict[UUID, List[str]] = {}
    for user_id, role_name in rows:
        role_map.setdefault(user_id, []).append(role_name)
    return role_map


class FarmOwnerOut(BaseModel):
    user_id: UUID
    email: str
    full_name: Optional[str]


class FarmMemberOut(BaseModel):
    user_id: UUID
    email: str
    full_name: Optional[str]
    roles: List[str]
    is_owner: bool


class FarmOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    owners: List[FarmOwnerOut]
    members: List[FarmMemberOut]
    can_edit: bool


class FarmCreate(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    owner_ids: Optional[List[UUID]] = None


class FarmUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    owner_ids: Optional[List[UUID]] = None


class FarmMemberAdd(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[EmailStr] = None

    @root_validator(pre=True)
    def validate_identifier(cls, values: Dict[str, Optional[str]]):
        user_id = values.get("user_id")
        email = values.get("email")
        if bool(user_id) == bool(email):
            raise ValueError("Provide exactly one of user_id or email")
        return values


def serialize_farm(
    farm: Farm, current_user: User, role_names: Set[str], db: Session
) -> FarmOut:
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
    member_roles = fetch_roles_for_users(db, {link.user_id for link in farm.user_links})
    members = [
        FarmMemberOut(
            user_id=link.user_id,
            email=link.user.email,
            full_name=link.user.full_name,
            roles=sorted(member_roles.get(link.user_id, [])),
            is_owner=link.is_owner,
        )
        for link in farm.user_links
    ]
    return FarmOut(
        id=farm.id,
        name=farm.name,
        created_at=farm.created_at,
        updated_at=farm.updated_at,
        owners=owners,
        members=members,
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


def resolve_user_from_payload(db: Session, payload: FarmMemberAdd) -> User:
    if payload.user_id:
        user = db.query(User).filter(User.id == payload.user_id).first()
    elif payload.email:
        email = payload.email.lower()
        user = db.query(User).filter(User.email == email).first()
    else:
        raise HTTPException(status_code=400, detail="User identifier is required")

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


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
    return [serialize_farm(farm, current, role_names, db) for farm in farms]


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
    return serialize_farm(farm, current, role_names, db)


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
    return serialize_farm(farm, current, role_names, db)


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

        existing_links = (
            db.query(UserFarm)
            .filter(UserFarm.farm_id == farm.id)
            .all()
        )
        existing_by_user = {link.user_id: link for link in existing_links}

        for link in existing_links:
            link.is_owner = link.user_id in new_owner_ids

        missing_owner_ids = new_owner_ids - set(existing_by_user.keys())
        for owner_id in missing_owner_ids:
            db.add(UserFarm(user_id=owner_id, farm_id=farm.id, is_owner=True))

    db.commit()

    farm = require_farm_access(db, current, farm_id, role_names)
    return serialize_farm(farm, current, role_names, db)


@router.post("/{farm_id}/members", response_model=FarmOut)
def add_farm_member(
    farm_id: UUID,
    payload: FarmMemberAdd,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    farm = require_farm_access(db, current, farm_id, role_names)
    target_user = resolve_user_from_payload(db, payload)
    target_roles = get_role_names(db, target_user)

    if not target_roles & ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail="User must have a farmer or technician role to be assigned to a farm",
        )

    if "admin" not in role_names and "technician" not in target_roles:
        raise HTTPException(
            status_code=403,
            detail="Farmers can only manage technician access",
        )

    link = (
        db.query(UserFarm)
        .filter(UserFarm.user_id == target_user.id, UserFarm.farm_id == farm.id)
        .first()
    )

    should_be_owner = "farmer" in target_roles

    if link:
        if should_be_owner and not link.is_owner:
            link.is_owner = True
    else:
        db.add(
            UserFarm(
                user_id=target_user.id,
                farm_id=farm.id,
                is_owner=should_be_owner,
            )
        )

    db.commit()

    updated_farm = base_query(db).filter(Farm.id == farm.id).first()
    if not updated_farm:
        raise HTTPException(status_code=500, detail="Failed to load farm")
    return serialize_farm(updated_farm, current, role_names, db)


@router.delete("/{farm_id}/members/{user_id}", response_model=FarmOut)
def remove_farm_member(
    farm_id: UUID,
    user_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_role_names(db, current)
    if not role_names & ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    farm = require_farm_access(db, current, farm_id, role_names)
    link = (
        db.query(UserFarm)
        .options(selectinload(UserFarm.user))
        .filter(UserFarm.user_id == user_id, UserFarm.farm_id == farm.id)
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="User is not associated with this farm")

    target_roles = get_role_names(db, link.user)

    if "admin" not in role_names:
        if link.is_owner or "technician" not in target_roles:
            raise HTTPException(
                status_code=403,
                detail="Farmers can only remove technicians from a farm",
            )
    else:
        if link.is_owner:
            remaining_owner_count = (
                db.query(UserFarm)
                .filter(
                    UserFarm.farm_id == farm.id,
                    UserFarm.is_owner.is_(True),
                    UserFarm.user_id != user_id,
                )
                .count()
            )
            if remaining_owner_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot remove the last remaining farm owner",
                )

    db.delete(link)
    db.commit()

    updated_farm = base_query(db).filter(Farm.id == farm.id).first()
    if not updated_farm:
        raise HTTPException(status_code=500, detail="Failed to load farm")
    return serialize_farm(updated_farm, current, role_names, db)
