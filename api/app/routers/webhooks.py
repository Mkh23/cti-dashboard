"""
Webhook endpoint for receiving S3 upload notifications from AWS Lambda.
Validates HMAC signature and meta.json schema.
"""
import json
import hmac
import hashlib
import logging
import os
from datetime import datetime
from typing import Optional

import jsonschema
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.ingest_service import ingest_scan_from_payload

router = APIRouter()
logger = logging.getLogger(__name__)

# HMAC secret from environment
HMAC_SECRET = os.getenv("HMAC_SECRET", "dev_secret_change_me")
# Allow override by env (default 5 minutes)
HMAC_WINDOW_SECONDS = int(os.getenv("HMAC_WINDOW_SECONDS", "300"))


def verify_hmac(timestamp: str, signature: str, body: bytes) -> bool:
    """Verify HMAC signature with timestamp."""
    try:
        ts = int(timestamp)
        now = int(datetime.utcnow().timestamp())
        drift = now - ts

        # Compute expected signature EXACTLY as used in compare
        body_str = body.decode()
        expected_hex = hmac.new(
            HMAC_SECRET.encode(),
            f"{timestamp}.{body_str}".encode(),
            hashlib.sha256
        ).hexdigest()
        expected_hdr = f"sha256={expected_hex}"

        if abs(drift) > HMAC_WINDOW_SECONDS:
            return False

        return hmac.compare_digest(expected_hdr, signature)
    except (ValueError, AttributeError) as exc:
        logger.warning("Failed to verify webhook signature: %s", exc)
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
    
    try:
        result = ingest_scan_from_payload(
            db,
            bucket=bucket,
            ingest_key=ingest_key,
            device_code=device_code,
            objects=objects,
            meta_json=meta_json,
            source="webhook",
            payload_size=len(body),
            started_at=start_time,
        )
    except jsonschema.ValidationError as e:
        error_msg = f"Schema validation failed: {e.message}"
        logger.warning("Schema validation failed: %s (path=%s)", e.message, list(e.path))
        raise HTTPException(status_code=400, detail=error_msg)
    
    return result
