"""
Scans API endpoints for viewing and managing scans.
Implements listing, detail views, and scan actions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from uuid import UUID
from datetime import datetime

from ..db import get_db
from ..models import Scan, ScanStatus, Device, Farm, Asset, User
from .me import get_current_user

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
    mask_asset_id: Optional[UUID]
    mask_bucket: Optional[str] = None
    mask_key: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PaginatedScans(BaseModel):
    scans: List[ScanOut]
    total: int
    page: int
    per_page: int
    total_pages: int


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
    
    # Add image asset info
    if scan.image_asset:
        result.image_bucket = scan.image_asset.bucket
        result.image_key = scan.image_asset.object_key
    
    # Add mask asset info
    if scan.mask_asset:
        result.mask_bucket = scan.mask_asset.bucket
        result.mask_key = scan.mask_asset.object_key
    
    return result
