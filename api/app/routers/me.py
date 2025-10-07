from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, UserRole, Role
from ..schemas import MeOut, UpdateProfile, ChangePassword
from ..security import decode_token, hash_password, verify_password

router = APIRouter()

def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    import uuid
    user_id = uuid.UUID(payload["sub"])
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.get("", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roles = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    role_names = [r[0] for r in roles]
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "address": user.address,
        "roles": role_names
    }

@router.put("", response_model=MeOut)
def update_profile(
    profile_data: UpdateProfile,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information."""
    # Update only provided fields
    if profile_data.full_name is not None:
        user.full_name = profile_data.full_name
    if profile_data.phone_number is not None:
        user.phone_number = profile_data.phone_number
    if profile_data.address is not None:
        user.address = profile_data.address
    
    db.commit()
    db.refresh(user)
    
    # Get roles for response
    roles = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    role_names = [r[0] for r in roles]
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "address": user.address,
        "roles": role_names
    }

@router.post("/password")
def change_password(
    password_data: ChangePassword,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not verify_password(password_data.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Hash and update new password
    user.hashed_password = hash_password(password_data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
