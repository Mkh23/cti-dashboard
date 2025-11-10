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



