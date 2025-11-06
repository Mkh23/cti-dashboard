"""
Scans API endpoints for viewing and managing scans.
Implements listing, detail views, and scan actions with role-based access control.
"""
from decimal import Decimal, ROUND_HALF_UP
from random import uniform
from typing import Dict, List, Optional, Set
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import (
    Asset,
    Device,
    Farm,
    GradingResult,
    Role,
    Scan,
    ScanStatus,
    User,
    UserFarm,
    UserRole,
)
from .me import get_current_user
from ..s3_utils import generate_presigned_url

router = APIRouter()


# ============ Schemas ============


class LatestGradingOut(BaseModel):
    id: Optional[UUID] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None


class GradingResultOut(BaseModel):
    id: UUID
    model_name: str
    model_version: str
    inference_sha256: Optional[str]
    confidence: Optional[float]
    confidence_breakdown: Optional[Dict[str, float]]
    features_used: Optional[Dict[str, float]]
    created_by: Optional[UUID]
    created_by_email: Optional[str]
    created_by_name: Optional[str]
    created_at: datetime


class ScanOut(BaseModel):
    id: UUID
    scan_id: Optional[str]
    capture_id: str
    ingest_key: str
    device_id: UUID
    device_code: Optional[str]
    device_label: Optional[str]
    farm_id: Optional[UUID]
    farm_name: Optional[str]
    animal_id: Optional[UUID]
    operator_id: Optional[UUID]
    captured_at: Optional[datetime]
    status: ScanStatus
    image_asset_id: Optional[UUID]
    mask_asset_id: Optional[UUID]
    created_at: datetime
    latest_grading: Optional[LatestGradingOut] = None


class ScanDetailOut(ScanOut):
    image_bucket: Optional[str] = None
    image_key: Optional[str] = None
    image_url: Optional[str] = None
    mask_bucket: Optional[str] = None
    mask_key: Optional[str] = None
    mask_url: Optional[str] = None
    grading_results: List[GradingResultOut] = Field(default_factory=list)


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


class GradeScanPayload(BaseModel):
    model_name: str = Field(default="cti-sim", max_length=255)
    model_version: str = Field(default="1.0.0", max_length=50)
    inference_sha256: Optional[str] = Field(default=None, max_length=64)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    confidence_breakdown: Optional[Dict[str, float]] = None
    features_used: Optional[Dict[str, float]] = None


# ============ Helper Functions ============

CONFIDENCE_STEP = Decimal("0.0001")


def get_user_roles(user: User, db: Session) -> Set[str]:
    """Get set of role names for a user."""
    roles = (
        db.query(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    return {r[0] for r in roles}


def is_admin(user: User, db: Session) -> bool:
    """Check if user has admin role."""
    return "admin" in get_user_roles(user, db)


def get_accessible_farm_ids(db: Session, user: User) -> Set[UUID]:
    rows = (
        db.query(UserFarm.farm_id)
        .filter(UserFarm.user_id == user.id)
        .all()
    )
    return {row[0] for row in rows}


def apply_visibility_filter(
    query,
    db: Session,
    user: User,
    role_names: Optional[Set[str]] = None,
):
    if role_names is None:
        role_names = get_user_roles(user, db)
    is_admin_role = "admin" in role_names
    if is_admin_role:
        return query, True, role_names

    accessible_farms = get_accessible_farm_ids(db, user)
    if accessible_farms:
        query = query.filter(
            or_(Scan.farm_id.in_(accessible_farms), Scan.operator_id == user.id)
        )
    else:
        query = query.filter(Scan.operator_id == user.id)
    return query, False, role_names


def ensure_scan_access(
    scan: Scan,
    db: Session,
    user: User,
    role_names: Optional[Set[str]] = None,
):
    if role_names is None:
        role_names = get_user_roles(user, db)
    if "admin" in role_names:
        return

    accessible_farms = get_accessible_farm_ids(db, user)
    if scan.farm_id and scan.farm_id in accessible_farms:
        return
    if scan.operator_id == user.id:
        return
    raise HTTPException(status_code=403, detail="Not authorized to access this scan")


def quantize_confidence(value: Optional[float]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value)).quantize(CONFIDENCE_STEP, rounding=ROUND_HALF_UP)


def latest_grading(grades: List[GradingResult]) -> Optional[GradingResult]:
    if not grades:
        return None
    return max(grades, key=lambda g: g.created_at)


def serialize_latest_grading(grade: Optional[GradingResult]) -> Optional[LatestGradingOut]:
    if not grade:
        return None
    return LatestGradingOut(
        id=grade.id,
        model_name=grade.model_name,
        model_version=grade.model_version,
        confidence=float(grade.confidence) if grade.confidence is not None else None,
        created_at=grade.created_at,
    )


def serialize_grading_result(grade: GradingResult) -> GradingResultOut:
    return GradingResultOut(
        id=grade.id,
        model_name=grade.model_name,
        model_version=grade.model_version,
        inference_sha256=grade.inference_sha256,
        confidence=float(grade.confidence) if grade.confidence is not None else None,
        confidence_breakdown=grade.confidence_breakdown,
        features_used=grade.features_used,
        created_by=grade.created_by,
        created_by_email=grade.creator.email if grade.creator else None,
        created_by_name=grade.creator.full_name if grade.creator else None,
        created_at=grade.created_at,
    )


def serialize_scan_summary(scan: Scan) -> ScanOut:
    latest = serialize_latest_grading(latest_grading(scan.grading_results))
    return ScanOut(
        id=scan.id,
        scan_id=scan.scan_id,
        capture_id=scan.capture_id,
        ingest_key=scan.ingest_key,
        device_id=scan.device_id,
        device_code=scan.device.device_code if scan.device else None,
        device_label=scan.device.label if scan.device else None,
        farm_id=scan.farm_id,
        farm_name=scan.farm.name if scan.farm else None,
        animal_id=scan.animal_id,
        operator_id=scan.operator_id,
        captured_at=scan.captured_at,
        status=scan.status,
        image_asset_id=scan.image_asset_id,
        mask_asset_id=scan.mask_asset_id,
        created_at=scan.created_at,
        latest_grading=latest,
    )


def serialize_scan_detail(scan: Scan) -> ScanDetailOut:
    summary = serialize_scan_summary(scan)
    grading_results = [
        serialize_grading_result(grade)
        for grade in sorted(scan.grading_results, key=lambda g: g.created_at, reverse=True)
    ]
    return ScanDetailOut(
        **summary.model_dump(),
        image_bucket=scan.image_asset.bucket if scan.image_asset else None,
        image_key=scan.image_asset.object_key if scan.image_asset else None,
        image_url=generate_presigned_url(
            scan.image_asset.bucket,
            scan.image_asset.object_key,
        )
        if scan.image_asset
        else None,
        mask_bucket=scan.mask_asset.bucket if scan.mask_asset else None,
        mask_key=scan.mask_asset.object_key if scan.mask_asset else None,
        mask_url=generate_presigned_url(
            scan.mask_asset.bucket,
            scan.mask_asset.object_key,
        )
        if scan.mask_asset
        else None,
        grading_results=grading_results,
    )


def load_scan_with_related(db: Session, scan_id: UUID) -> Scan:
    scan = (
        db.query(Scan)
        .options(
            selectinload(Scan.device),
            selectinload(Scan.farm),
            selectinload(Scan.image_asset),
            selectinload(Scan.mask_asset),
            selectinload(Scan.grading_results).selectinload(GradingResult.creator),
        )
        .filter(Scan.id == scan_id)
        .first()
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


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
    role_names = get_user_roles(current, db)

    query = (
        db.query(Scan)
        .options(
            selectinload(Scan.device),
            selectinload(Scan.farm),
            selectinload(Scan.image_asset),
            selectinload(Scan.mask_asset),
            selectinload(Scan.grading_results),
        )
    )

    query, _, _ = apply_visibility_filter(query, db, current, role_names)

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
    scans = (
        query.offset(offset)
        .limit(per_page)
        .all()
    )
    
    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page
    
    return PaginatedScans(
        scans=[serialize_scan_summary(scan) for scan in scans],
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
    role_names = get_user_roles(current, db)
    query = db.query(Scan)
    query, _, _ = apply_visibility_filter(query, db, current, role_names)

    total = query.count()

    status_counts = (
        query.with_entities(Scan.status, func.count(Scan.id))
        .group_by(Scan.status)
        .all()
    )
    by_status = {status.value: count for status, count in status_counts}

    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_count = query.filter(Scan.created_at >= yesterday).count()

    return ScanStatsOut(total=total, by_status=by_status, recent_count=recent_count)


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
    role_names = get_user_roles(current, db)
    scan = load_scan_with_related(db, scan_id)
    ensure_scan_access(scan, db, current, role_names)
    return serialize_scan_detail(scan)


@router.post("/{scan_id}/grade", response_model=ScanDetailOut)
def grade_scan(
    scan_id: UUID,
    payload: GradeScanPayload,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role_names = get_user_roles(current, db)
    if not {"admin", "technician"} & role_names:
        raise HTTPException(status_code=403, detail="Only admins or technicians can grade scans")

    scan = load_scan_with_related(db, scan_id)
    ensure_scan_access(scan, db, current, role_names)

    confidence_value = payload.confidence
    if confidence_value is None:
        confidence_value = round(uniform(0.65, 0.98), 4)

    grade = GradingResult(
        scan_id=scan.id,
        model_name=payload.model_name,
        model_version=payload.model_version,
        inference_sha256=payload.inference_sha256,
        confidence=quantize_confidence(confidence_value),
        confidence_breakdown=payload.confidence_breakdown,
        features_used=payload.features_used,
        created_by=current.id,
    )

    scan.status = ScanStatus.graded
    db.add(grade)
    db.commit()

    updated_scan = load_scan_with_related(db, scan.id)
    return serialize_scan_detail(updated_scan)
