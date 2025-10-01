"""
Webhook endpoint for receiving S3 upload notifications from AWS Lambda.
Validates HMAC signature and meta.json schema.
"""
import os
import json
import hmac
import hashlib
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
import jsonschema

from ..db import get_db
from ..models import Device, Scan, Asset, ScanEvent, IngestionLog, ScanStatus

router = APIRouter()

# Load meta.json schema
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "meta_v1.json"
with open(SCHEMA_PATH) as f:
    META_SCHEMA = json.load(f)

# HMAC secret from environment
HMAC_SECRET = os.getenv("HMAC_SECRET", "dev_secret_change_me")
HMAC_WINDOW_SECONDS = 300  # Allow ±5 minutes


def verify_hmac(timestamp: str, signature: str, body: bytes) -> bool:
    """Verify HMAC signature with timestamp."""
    try:
        # Check timestamp is within window
        ts = int(timestamp)
        now = int(datetime.utcnow().timestamp())
        if abs(now - ts) > HMAC_WINDOW_SECONDS:
            return False
        
        # Verify signature
        expected = hmac.new(
            HMAC_SECRET.encode(),
            f"{timestamp}.{body.decode()}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(f"sha256={expected}", signature)
    except (ValueError, AttributeError):
        return False


@router.post("/webhook")
async def ingest_webhook(
    request: Request,
    x_cti_timestamp: Optional[str] = Header(None, alias="X-CTI-Timestamp"),
    x_cti_signature: Optional[str] = Header(None, alias="X-CTI-Signature"),
    db: Session = Depends(get_db)
):
    """
    Receive webhook from Lambda with signed S3 upload notification.
    
    Expected payload:
    {
        "bucket": "cti-dev-406214277746",
        "ingest_key": "raw/dev-0001/2025/09/09/cap_1757423584/",
        "device_code": "dev-0001",
        "objects": ["image.jpg", "meta.json"],
        "meta_json": { ... }
    }
    """
    start_time = datetime.utcnow()
    body = await request.body()
    
    # Verify HMAC signature
    if not x_cti_timestamp or not x_cti_signature:
        raise HTTPException(status_code=401, detail="Missing HMAC headers")
    
    if not verify_hmac(x_cti_timestamp, x_cti_signature, body):
        raise HTTPException(status_code=403, detail="Invalid signature or timestamp")
    
    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Extract required fields
    bucket = payload.get("bucket")
    ingest_key = payload.get("ingest_key")
    device_code = payload.get("device_code")
    objects = payload.get("objects", [])
    meta_json = payload.get("meta_json")
    
    if not all([bucket, ingest_key, device_code, meta_json]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Validate meta.json against schema
    try:
        jsonschema.validate(instance=meta_json, schema=META_SCHEMA)
    except jsonschema.ValidationError as e:
        error_msg = f"Schema validation failed: {e.message}"
        log_ingestion(db, meta_json.get("capture_id", "unknown"), ingest_key, 400, len(body), 
                     int((datetime.utcnow() - start_time).total_seconds() * 1000), error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    capture_id = meta_json["capture_id"]
    
    # Check idempotency - if scan already exists with this ingest_key, return success
    existing = db.query(Scan).filter_by(ingest_key=ingest_key).first()
    if existing:
        log_ingestion(db, capture_id, ingest_key, 200, len(body),
                     int((datetime.utcnow() - start_time).total_seconds() * 1000), None)
        return {"status": "duplicate", "scan_id": str(existing.id), "message": "Scan already ingested"}
    
    # Upsert device
    device = db.query(Device).filter_by(device_code=device_code).first()
    if not device:
        device = Device(
            device_code=device_code,
            s3_prefix_hint=f"raw/{device_code}/",
            last_upload_at=datetime.utcnow(),
            captures_count=1
        )
        db.add(device)
    else:
        device.last_upload_at = datetime.utcnow()
        device.captures_count += 1
    
    db.flush()  # Get device.id
    
    # Create asset records
    image_asset = None
    mask_asset = None
    
    for obj in objects:
        if obj == meta_json["files"]["image_relpath"]:
            # Create image asset
            image_asset = Asset(
                bucket=bucket,
                object_key=f"{ingest_key}{obj}",
                sha256=meta_json["image_sha256"],
                mime_type="image/jpeg" if obj.endswith(".jpg") else "image/png"
            )
            db.add(image_asset)
        elif meta_json["files"].get("mask_relpath") and obj == meta_json["files"]["mask_relpath"]:
            # Create mask asset
            mask_asset = Asset(
                bucket=bucket,
                object_key=f"{ingest_key}{obj}",
                sha256=meta_json.get("mask_sha256", ""),
                mime_type="image/png"
            )
            db.add(mask_asset)
    
    db.flush()  # Get asset IDs
    
    # Create scan record
    gps_point = None
    if meta_json.get("gps"):
        # PostGIS Point(lon, lat)
        gps_point = ST_SetSRID(ST_MakePoint(meta_json["gps"]["lon"], meta_json["gps"]["lat"]), 4326)
    
    scan = Scan(
        capture_id=capture_id,
        ingest_key=ingest_key,
        device_id=device.id,
        captured_at=datetime.fromisoformat(meta_json["captured_at"].replace("Z", "+00:00")),
        status=ScanStatus.ingested,
        image_asset_id=image_asset.id if image_asset else None,
        mask_asset_id=mask_asset.id if mask_asset else None,
        gps=gps_point
    )
    db.add(scan)
    db.flush()
    
    # Create scan event
    event = ScanEvent(
        scan_id=scan.id,
        event="ingested",
        meta={
            "source": "webhook",
            "device_code": device_code,
            "objects": objects,
            "firmware": meta_json.get("firmware"),
            "probe": meta_json.get("probe")
        }
    )
    db.add(event)
    
    # Log successful ingestion
    elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    log_ingestion(db, capture_id, ingest_key, 200, len(body), elapsed_ms, None)
    
    db.commit()
    
    return {
        "status": "success",
        "scan_id": str(scan.id),
        "capture_id": capture_id,
        "message": "Scan ingested successfully"
    }


def log_ingestion(db: Session, capture_id: str, ingest_key: str, status: int, bytes_in: int, ms: int, error: Optional[str]):
    """Log ingestion attempt."""
    log = IngestionLog(
        capture_id=capture_id,
        ingest_key=ingest_key,
        http_status=status,
        bytes_in=bytes_in,
        ms=ms,
        error=error
    )
    db.add(log)
    db.commit()
