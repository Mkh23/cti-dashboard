import os
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, Role, UserRole, Device
from ..services.sync_service import sync_scans_from_bucket
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

# ============ Schemas ============

class UserWithRoles(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    roles: List[str]

class UpdateRolesPayload(BaseModel):
    roles: List[str]

class DeviceOut(BaseModel):
    id: UUID
    device_code: str
    label: Optional[str]
    farm_id: Optional[UUID]
    s3_prefix_hint: Optional[str]
    last_seen_at: Optional[datetime]
    last_upload_at: Optional[datetime]
    captures_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DeviceCreate(BaseModel):
    device_code: str
    label: Optional[str] = None
    farm_id: Optional[UUID] = None
    s3_prefix_hint: Optional[str] = None

class DeviceUpdate(BaseModel):
    label: Optional[str] = None
    farm_id: Optional[UUID] = None


class SyncScansPayload(BaseModel):
    mode: Literal["add_only", "add_remove"] = "add_only"
    prefix: Optional[str] = "raw/"


class SyncScansResult(BaseModel):
    bucket: str
    prefix: str
    mode: str
    added: int
    duplicates: int
    removed: int
    errors: List[str]
    synced_ingest_keys: int

# ============ User Management ============

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

        out.append(
            UserWithRoles(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                roles=role_names,
            )
        )
    return out

@router.put("/users/{user_id}/roles", response_model=UserWithRoles)
def set_roles(user_id: UUID, payload: UpdateRolesPayload, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
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

    return UserWithRoles(
        id=u.id,
        email=u.email,
        full_name=u.full_name,
        roles=payload.roles,
    )


# ============ Device Management ============

@router.get("/devices", response_model=List[DeviceOut])
def list_devices(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all devices."""
    require_admin(current, db)
    devices = db.query(Device).order_by(Device.device_code).all()
    return devices

@router.post("/devices", response_model=DeviceOut)
def create_device(payload: DeviceCreate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Register a new device."""
    require_admin(current, db)
    
    # Check if device already exists
    existing = db.query(Device).filter_by(device_code=payload.device_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device code already exists")
    
    device = Device(
        device_code=payload.device_code,
        label=payload.label,
        farm_id=payload.farm_id,
        s3_prefix_hint=payload.s3_prefix_hint or f"raw/{payload.device_code}/"
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

@router.get("/devices/{device_id}", response_model=DeviceOut)
def get_device(device_id: UUID, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get device by ID."""
    require_admin(current, db)
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

@router.put("/devices/{device_id}", response_model=DeviceOut)
def update_device(device_id: UUID, payload: DeviceUpdate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update device details."""
    require_admin(current, db)
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if payload.label is not None:
        device.label = payload.label
    if payload.farm_id is not None:
        device.farm_id = payload.farm_id
    
    db.commit()
    db.refresh(device)
    return device


# ============ Database Sync ============

@router.post("/database/sync-scans", response_model=SyncScansResult)
def admin_sync_scans(
    payload: SyncScansPayload,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger a best-effort sync between AWS S3 and the scans table."""
    require_admin(current, db)
    bucket = os.getenv("CTI_BUCKET", "cti-dev-406214277746")
    prefix = (payload.prefix or "raw/").lstrip("/")
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"

    result = sync_scans_from_bucket(
        db,
        bucket=bucket,
        prefix=prefix,
        mode=payload.mode,
    )
    return result
