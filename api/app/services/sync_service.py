"""
Utilities for syncing scans between S3 and Postgres via the admin panel.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set

import jsonschema
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Asset, Scan, ScanEvent
from ..s3_utils import get_s3_client
from .ingest_service import ingest_scan_from_payload

logger = logging.getLogger(__name__)


def _list_meta_keys(s3, bucket: str, prefix: str) -> Iterable[str]:
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("meta.json"):
                yield key


def _list_objects_in_capture(s3, bucket: str, ingest_key: str) -> List[str]:
    """Return object names (relative to ingest_key) for a capture folder."""
    objects: List[str] = []
    continuation_token: Optional[str] = None
    while True:
        params: Dict[str, object] = {
            "Bucket": bucket,
            "Prefix": ingest_key,
            "MaxKeys": 1000,
        }
        if continuation_token:
            params["ContinuationToken"] = continuation_token
        resp = s3.list_objects_v2(**params)
        for item in resp.get("Contents", []):
            key = item["Key"]
            if key.endswith("/"):
                continue
            relative = key[len(ingest_key) :]
            objects.append(relative)
        if not resp.get("IsTruncated"):
            break
        continuation_token = resp.get("NextContinuationToken")
    return objects


def _delete_scan(db: Session, scan: Scan) -> None:
    """Delete scan plus related assets/events."""
    db.query(ScanEvent).filter(ScanEvent.scan_id == scan.id).delete()

    asset_ids = [scan.image_asset_id, scan.mask_asset_id]
    for asset_id in asset_ids:
        if asset_id:
            asset = db.get(Asset, asset_id)
            if asset:
                db.delete(asset)

    db.delete(scan)


def sync_scans_from_bucket(
    db: Session,
    *,
    bucket: str,
    prefix: str,
    mode: str,
    s3_client=None,
) -> Dict[str, object]:
    """
    Synchronize scans by reading meta.json files from S3.

    mode:
      - "add_only": ingest missing scans
      - "add_remove": ingest missing scans and remove DB scans whose ingest_key isn't present
    """
    s3 = s3_client or get_s3_client()
    added = 0
    duplicates = 0
    errors: List[str] = []
    ingest_keys_seen: Set[str] = set()

    try:
        for meta_key in _list_meta_keys(s3, bucket, prefix):
            try:
                capture_prefix = meta_key.rsplit("/", 1)[0] + "/"
                ingest_keys_seen.add(capture_prefix)

                meta_obj = s3.get_object(Bucket=bucket, Key=meta_key)
                raw_body = meta_obj["Body"].read()
                payload_size = len(raw_body)
                meta_json = json.loads(raw_body.decode("utf-8"))
                device_code = meta_json.get("device_code")
                if not device_code:
                    raise ValueError("meta_json missing device_code")

                objects = _list_objects_in_capture(s3, bucket, capture_prefix)
                try:
                    result = ingest_scan_from_payload(
                        db,
                        bucket=bucket,
                        ingest_key=capture_prefix,
                        device_code=device_code,
                        objects=objects,
                        meta_json=meta_json,
                        source="admin_sync",
                        payload_size=payload_size,
                        started_at=datetime.utcnow(),
                    )
                except jsonschema.ValidationError as ve:
                    raise ValueError(
                        f"Schema validation failed for {meta_key}: {ve.message}"
                    ) from ve

                if result["created"]:
                    added += 1
                else:
                    duplicates += 1
            except Exception as exc:  # noqa: BLE001
                msg = f"{meta_key}: {exc}"
                logger.warning("Failed to sync %s", msg)
                errors.append(msg)
    except NoCredentialsError as exc:
        logger.error("AWS credentials missing while syncing scans: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="AWS credentials not configured for scan sync",
        ) from exc
    except ClientError as exc:
        logger.error("AWS client error during scan sync: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=400,
            detail=f"AWS error while listing {bucket}/{prefix}: {exc}",
        ) from exc

    removed = 0
    if mode == "add_remove" and ingest_keys_seen:
        scans_to_remove = (
            db.query(Scan)
            .filter(Scan.ingest_key.like(f"{prefix}%"))
            .filter(~Scan.ingest_key.in_(ingest_keys_seen))
            .all()
        )
        for scan in scans_to_remove:
            _delete_scan(db, scan)
            removed += 1
        if removed:
            db.commit()

    return {
        "bucket": bucket,
        "prefix": prefix,
        "mode": mode,
        "added": added,
        "duplicates": duplicates,
        "removed": removed,
        "errors": errors,
        "synced_ingest_keys": len(ingest_keys_seen),
    }
