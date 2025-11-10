"""
Utilities for syncing scans between S3 and Postgres via the admin panel.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set

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

def _raise_aws_error(exc: Exception, *, bucket: str, prefix: str) -> None:
    if isinstance(exc, NoCredentialsError):
        raise HTTPException(
            status_code=400,
            detail="AWS credentials not configured for scan sync",
        ) from exc
    if isinstance(exc, ClientError):
        raise HTTPException(
            status_code=400,
            detail=f"AWS error while accessing s3://{bucket}/{prefix}: {exc}",
        ) from exc
    raise HTTPException(
        status_code=400,
        detail=f"AWS error while accessing s3://{bucket}/{prefix}: {exc}",
    ) from exc

def _ensure_trailing_slash(value: str) -> str:
    if value and not value.endswith("/"):
        return f"{value}/"
    return value


def sync_scans_from_bucket(
    db: Session,
    *,
    bucket: str,
    prefix: str,
    mode: str,
    s3_client=None,
) -> Dict[str, object]:
    """
    Crawl an S3 prefix for meta.json files and upsert scans accordingly.
    """
    if mode not in {"add_only", "add_remove"}:
        raise HTTPException(status_code=400, detail=f"Unsupported mode '{mode}'")

    s3 = s3_client or get_s3_client()
    prefix = prefix.lstrip("/")
    prefix = _ensure_trailing_slash(prefix)

    added = 0
    duplicates = 0
    removed = 0
    errors: List[str] = []
    synced_ingest: Set[str] = set()

    try:
        meta_keys = list(_list_meta_keys(s3, bucket, prefix))
    except (ClientError, NoCredentialsError) as exc:  # pragma: no cover - network path
        _raise_aws_error(exc, bucket=bucket, prefix=prefix)

    for meta_key in meta_keys:
        ingest_key = _ensure_trailing_slash(meta_key.rsplit("/", 1)[0])
        synced_ingest.add(ingest_key)

        existing = db.query(Scan).filter(Scan.ingest_key == ingest_key).first()
        if existing:
            duplicates += 1
            continue

        try:
            response = s3.get_object(Bucket=bucket, Key=meta_key)
            body = response["Body"].read()
            payload_size = len(body)
            meta_json = json.loads(body)
        except jsonschema.ValidationError as exc:
            errors.append(f"{meta_key}: schema error - {exc.message}")
            continue
        except json.JSONDecodeError as exc:
            errors.append(f"{meta_key}: invalid JSON ({exc})")
            continue
        except (ClientError, NoCredentialsError) as exc:  # pragma: no cover - network path
            _raise_aws_error(exc, bucket=bucket, prefix=meta_key)

        try:
            objects = _list_objects_in_capture(s3, bucket, ingest_key)
        except (ClientError, NoCredentialsError) as exc:  # pragma: no cover - network path
            _raise_aws_error(exc, bucket=bucket, prefix=ingest_key)

        device_code = meta_json.get("device_code") or "unknown-device"
        result = ingest_scan_from_payload(
            db,
            bucket=bucket,
            ingest_key=ingest_key,
            device_code=device_code,
            objects=objects,
            meta_json=meta_json,
            source="admin_sync",
            payload_size=payload_size,
        )
        if result.get("created"):
            added += 1
        else:
            duplicates += 1

    if mode == "add_remove":
        existing_query = db.query(Scan)
        if prefix:
            existing_query = existing_query.filter(Scan.ingest_key.like(f"{prefix}%"))
        stale_scans = existing_query.filter(~Scan.ingest_key.in_(synced_ingest)).all()
        for scan in stale_scans:
            _delete_scan(db, scan)
            removed += 1
        if stale_scans:
            db.commit()

    return {
        "bucket": bucket,
        "prefix": prefix,
        "mode": mode,
        "added": added,
        "duplicates": duplicates,
        "removed": removed,
        "errors": errors,
        "synced_ingest_keys": len(synced_ingest),
    }
