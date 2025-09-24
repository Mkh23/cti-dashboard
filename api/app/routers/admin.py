from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Role, UserRole
from .me import get_current_user  # uses Bearer token

router = APIRouter()

def require_admin(user: User, db: Session):
    has_admin = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id, Role.name == "admin")
        .first()
    )
    if not has_admin:
        raise HTTPException(status_code=403, detail="Admin only")

class UserWithRoles(BaseModel):
    id: int
    email: str
    roles: List[str]

class UpdateRolesPayload(BaseModel):
    roles: List[str]

@router.get("/users", response_model=List[UserWithRoles])
def list_users(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current, db)
    users = db.query(User).all()
    out: List[UserWithRoles] = []
    for u in users:
        
        role_names = [
            r.name
            for r in (
                db.query(Role)
                .join(UserRole, Role.id == UserRole.role_id)
                .filter(UserRole.user_id == u.id)
                .all()
            )
        ]

        out.append(UserWithRoles(id=u.id, email=u.email, roles=role_names))
    return out

@router.put("/users/{user_id}/roles", response_model=UserWithRoles)
def set_roles(user_id: int, payload: UpdateRolesPayload, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_admin(current, db)
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    valid_roles = {r.name: r for r in db.query(Role).all()}
    for rn in payload.roles:
        if rn not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Unknown role: {rn}")

    db.query(UserRole).filter(UserRole.user_id == u.id).delete()
    for rn in payload.roles:
        db.add(UserRole(user_id=u.id, role_id=valid_roles[rn].id))
    db.commit()

    return UserWithRoles(id=u.id, email=u.email, roles=payload.roles)
