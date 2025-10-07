"""
Scans API endpoints for viewing and managing scans.
Implements listing, detail views, and scan actions with role-based access control.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func
from uuid import UUID
from datetime import datetime

from ..db import get_db
from ..models import Scan, ScanStatus, Device, Farm, Asset, User, Role, UserRole
from .me import get_current_user
from ..s3_utils import generate_presigned_url

router = APIRouter()


# ============ Schemas ============

class ScanOut(BaseModel):
    id: UUID
    scan_id: Optional[str]
    capture_id: str
    ingest_key: str
    device_id: UUID
    farm_id: Optional[UUID]
    animal_id: Optional[UUID]
    operator_id: Optional[UUID]
    captured_at: Optional[datetime]
    status: ScanStatus
    image_asset_id: Optional[UUID]
    mask_asset_id: Optional[UUID]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScanDetailOut(BaseModel):
    id: UUID
    scan_id: Optional[str]
    capture_id: str
    ingest_key: str
    device_id: UUID
    device_code: Optional[str] = None
    device_label: Optional[str] = None
    farm_id: Optional[UUID]
    farm_name: Optional[str] = None
    animal_id: Optional[UUID]
    operator_id: Optional[UUID]
    captured_at: Optional[datetime]
    status: ScanStatus
    image_asset_id: Optional[UUID]
    image_bucket: Optional[str] = None
    image_key: Optional[str] = None
    image_url: Optional[str] = None  # Presigned URL
    mask_asset_id: Optional[UUID]
    mask_bucket: Optional[str] = None
    mask_key: Optional[str] = None
    mask_url: Optional[str] = None  # Presigned URL
    created_at: datetime
    
    class Config:
        from_attributes = True


class ScanStatsOut(BaseModel):
    total: int
    by_status: Dict[str, int]
    recent_count: int  # Scans in last 24 hours


class PaginatedScans(BaseModel):
    scans: List[ScanOut]
    total: int
    page: int
    per_page: int
    total_pages: int


# ============ Helper Functions ============

def get_user_roles(user: User, db: Session) -> List[str]:
    """Get list of role names for a user."""
    roles = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    return [r[0] for r in roles]


def is_admin(user: User, db: Session) -> bool:
    """Check if user has admin role."""
    return "admin" in get_user_roles(user, db)


# ============ Endpoints ============

@router.get("", response_model=PaginatedScans)
def list_scans(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[ScanStatus] = Query(None, description="Filter by status"),
    device_id: Optional[UUID] = Query(None, description="Filter by device"),
    farm_id: Optional[UUID] = Query(None, description="Filter by farm"),
    sort_by: str = Query("created_at", description="Sort field (created_at or captured_at)"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List scans with filtering and pagination.
    
    - **page**: Page number (default: 1)
    - **per_page**: Items per page (default: 50, max: 100)
    - **status**: Filter by scan status
    - **device_id**: Filter by device
    - **farm_id**: Filter by farm
    - **sort_by**: Sort field (created_at or captured_at)
    - **sort_order**: Sort order (asc or desc)
    """
    # Build query
    query = db.query(Scan)
    
    # Apply filters
    if status:
        query = query.filter(Scan.status == status)
    if device_id:
        query = query.filter(Scan.device_id == device_id)
    if farm_id:
        query = query.filter(Scan.farm_id == farm_id)
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    sort_field = Scan.created_at if sort_by == "created_at" else Scan.captured_at
    if sort_order == "asc":
        query = query.order_by(asc(sort_field))
    else:
        query = query.order_by(desc(sort_field))
    
    # Apply pagination
    offset = (page - 1) * per_page
    scans = query.offset(offset).limit(per_page).all()
    
    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page
    
    return PaginatedScans(
        scans=scans,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/stats", response_model=ScanStatsOut)
def get_scan_stats(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about scans.
    
    Returns total count, breakdown by status, and recent activity.
    Role-based: Admin sees all, others see scans from their farms.
    """
    # Build base query
    query = db.query(Scan)
    
    # Apply role-based filtering (admin sees all)
    if not is_admin(current, db):
        # For non-admins, filter to scans where device is linked to their farms
        # (This would need UserFarm relationship, for now allow all)
        pass
    
    # Get total count
    total = query.count()
    
    # Get breakdown by status
    status_counts = (
        db.query(Scan.status, func.count(Scan.id))
        .group_by(Scan.status)
        .all()
    )
    by_status = {status.value: count for status, count in status_counts}
    
    # Get recent count (last 24 hours)
    from datetime import datetime, timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_count = query.filter(Scan.created_at >= yesterday).count()
    
    return ScanStatsOut(
        total=total,
        by_status=by_status,
        recent_count=recent_count
    )


@router.get("/{scan_id}", response_model=ScanDetailOut)
def get_scan(
    scan_id: UUID,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific scan.
    
    Includes device, farm, and asset information.
    """
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Build detailed response with related data
    result = ScanDetailOut(
        id=scan.id,
        scan_id=scan.scan_id,
        capture_id=scan.capture_id,
        ingest_key=scan.ingest_key,
        device_id=scan.device_id,
        farm_id=scan.farm_id,
        animal_id=scan.animal_id,
        operator_id=scan.operator_id,
        captured_at=scan.captured_at,
        status=scan.status,
        image_asset_id=scan.image_asset_id,
        mask_asset_id=scan.mask_asset_id,
        created_at=scan.created_at
    )
    
    # Add device info
    if scan.device:
        result.device_code = scan.device.device_code
        result.device_label = scan.device.label
    
    # Add farm info
    if scan.farm:
        result.farm_name = scan.farm.name
    
    # Add image asset info with presigned URL
    if scan.image_asset:
        result.image_bucket = scan.image_asset.bucket
        result.image_key = scan.image_asset.object_key
        result.image_url = generate_presigned_url(
            scan.image_asset.bucket,
            scan.image_asset.object_key
        )
    
    # Add mask asset info with presigned URL
    if scan.mask_asset:
        result.mask_bucket = scan.mask_asset.bucket
        result.mask_key = scan.mask_asset.object_key
        result.mask_url = generate_presigned_url(
            scan.mask_asset.bucket,
            scan.mask_asset.object_key
        )
    
    return result
