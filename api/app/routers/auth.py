import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from ..db import get_db, Base, engine
from ..models import User, Role, UserRole
from ..schemas import UserRegistration, Token, UserOut
from ..security import hash_password, verify_password, create_token
from ..models import RegistrationStatus

router = APIRouter()

# Note: Tables are now created via Alembic migrations
# Run: alembic upgrade head

@router.post("/register", response_model=UserOut)
def register(payload: UserRegistration, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check that roles are seeded in database
    admin_role = db.query(Role).filter_by(name="admin").first()
    technician_role = db.query(Role).filter_by(name="technician").first()
    
    if not admin_role or not technician_role:
        raise HTTPException(
            status_code=500, 
            detail="Database not properly initialized. Please run migrations: alembic upgrade head"
        )
    
    any_admin = db.query(UserRole).join(Role).filter(Role.name == "admin").first()
    status = RegistrationStatus.approved if not any_admin else RegistrationStatus.pending
    is_active = status == RegistrationStatus.approved

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        address=payload.address,
        registration_status=status,
        requested_role=payload.requested_role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    if status == RegistrationStatus.approved:
        db.add(UserRole(user_id=user.id, role_id=admin_role.id))
        db.commit()

    return user

@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.registration_status != RegistrationStatus.approved or not user.is_active:
        raise HTTPException(status_code=403, detail="Account pending approval")
    token = create_token(str(user.id))
    return {"access_token": token, "token_type": "bearer"}
