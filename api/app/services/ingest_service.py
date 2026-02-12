"""
Shared ingestion helpers so webhook and admin sync flows stay consistent.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

import jsonschema
from geoalchemy2.functions import ST_MakePoint, ST_SetSRID
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import (
    Animal,
    Asset,
    Group,
    Device,
    Farm,
    FarmGeofence,
    IngestionLog,
    Scan,
    ScanEvent,
    ScanStatus,
    ScanQuality,
)

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "meta_v1.json"
with SCHEMA_PATH.open() as f:
    META_SCHEMA = json.load(f)


def _apply_meta_defaults(meta_json: Dict) -> Dict:
    """Return a copy of meta_json with safe defaults for missing fields."""
    if not isinstance(meta_json, dict):
        raise ValueError("meta_json must be an object")

    data = dict(meta_json)

    # Essential identifiers
    data.setdefault("meta_version", "1.0.0")
    data.setdefault("device_code", "unknown-device")
    data.setdefault("capture_id", f"cap_{int(datetime.utcnow().timestamp())}")
    data.setdefault("captured_at", datetime.utcnow().isoformat() + "Z")
    data.setdefault("image_sha256", "0" * 64)
    data.setdefault("group_id", None)

    # Nested files structure
    files = data.get("files") if isinstance(data.get("files"), dict) else {}
    files = dict(files)
    files.setdefault("image_relpath", "image.jpg")
    files.setdefault("mask_relpath", None)
    files.setdefault("backfat_line_relpath", None)
    data["files"] = files

    # Required objects with minimal defaults
    probe = data.get("probe") if isinstance(data.get("probe"), dict) else {}
    probe = dict(probe)
    probe.setdefault("model", "unknown")
    data["probe"] = probe

    firmware = data.get("firmware") if isinstance(data.get("firmware"), dict) else {}
    firmware = dict(firmware)
    firmware.setdefault("app_version", "unknown")
    data["firmware"] = firmware

    # Legacy fields we intentionally ignore
    data.pop("cattle_ID", None)
    data.pop("cattle_id", None)

    return data


def validate_meta(meta_json: Dict) -> Dict:
    """Validate meta_json after applying defaults; returns normalized payload."""
    normalized = _apply_meta_defaults(meta_json)
    jsonschema.validate(instance=normalized, schema=META_SCHEMA)
    return normalized


def parse_decimal(value: Optional[object]) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


QUALITY_VALUES = {"good", "medium", "bad"}


def normalize_quality(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in QUALITY_VALUES:
            return normalized
    return None


def get_or_create_group(
    db: Session,
    *,
    external_id: Optional[str],
    farm_id: Optional[UUID],
    name_hint: Optional[str],
) -> Optional[Group]:
    if not external_id and not name_hint:
        return None

    query = db.query(Group)
    if external_id:
        group = query.filter(Group.external_id == external_id).first()
        if group:
            if farm_id and not group.farm_id:
                group.farm_id = farm_id
            return group

    group = Group(
        name=name_hint or external_id or "Auto herd",
        external_id=external_id,
        farm_id=farm_id,
    )
    db.add(group)
    db.flush()
    return group


def get_or_create_animal(
    db: Session,
    *,
    rfid: Optional[str],
    farm_id: Optional[UUID],
    group: Optional[Group],
) -> Optional[Animal]:
    if not rfid and not group:
        return None

    if rfid:
        animal = db.query(Animal).filter(Animal.rfid == rfid).first()
        if animal:
            updated = False
            if group and animal.group_id != group.id:
                animal.group_id = group.id
                updated = True
            if farm_id and animal.farm_id != farm_id:
                animal.farm_id = farm_id
                updated = True
            if updated:
                db.flush()
            return animal

    animal = Animal(
        tag_id=rfid or f"auto-tag-{datetime.utcnow().timestamp()}",
        rfid=rfid,
        farm_id=farm_id,
        group_id=group.id if group else None,
    )
    db.add(animal)
    db.flush()
    return animal


def find_farm_for_point(db: Session, point):
    """Return the farm_id whose geofence contains the provided point."""
    if point is None:
        return None

    geofence = (
        db.query(FarmGeofence)
        .filter(FarmGeofence.geometry != None)
        .filter(func.ST_Contains(FarmGeofence.geometry, point))
        .order_by(FarmGeofence.created_at.desc())
        .first()
    )
    if geofence:
        return geofence.farm_id

    farm = (
        db.query(Farm)
        .filter(Farm.geofence != None)
        .filter(func.ST_Contains(Farm.geofence, point))
        .order_by(Farm.updated_at.desc())
        .first()
    )
    if farm:
        return farm.id
    return None


def log_ingestion(
    db: Session,
    capture_id: str,
    ingest_key: str,
    status: int,
    bytes_in: int,
    ms: int,
    error: Optional[str],
) -> None:
    """Persist ingestion attempt."""
    log = IngestionLog(
        capture_id=capture_id,
        ingest_key=ingest_key,
        http_status=status,
        bytes_in=bytes_in,
        ms=ms,
        error=error,
    )
    db.add(log)
    db.commit()


def ingest_scan_from_payload(
    db: Session,
    *,
    bucket: str,
    ingest_key: str,
    device_code: str,
    objects: List[str],
    meta_json: Dict,
    source: str,
    payload_size: int,
    started_at: Optional[datetime] = None,
) -> Dict[str, object]:
    """
    Persist scan/asset records using the same flow as the webhook.
    Returns metadata indicating whether a new scan was created.
    """
    meta_json = validate_meta(meta_json)

    capture_id = meta_json["capture_id"]
    grading = meta_json.get("grading") or ""
    imf = parse_decimal(meta_json.get("IMF"))
    backfat_value = parse_decimal(meta_json.get("backfat_thickness"))
    animal_weight = parse_decimal(meta_json.get("animal_weight"))
    ribeye_area = parse_decimal(meta_json.get("ribeye_area"))
    animal_rfid = meta_json.get("Animal_RFID") or meta_json.get("animal_rfid")
    group_external_id = meta_json.get("group_ID") or meta_json.get("group_id")
    clarity_value = normalize_quality(meta_json.get("clarity"))
    usability_value = normalize_quality(meta_json.get("usability"))
    label_value = meta_json.get("label")
    label = label_value.strip() if isinstance(label_value, str) and label_value.strip() else None

    existing = db.query(Scan).filter_by(ingest_key=ingest_key).first()
    if existing:
        log_ingestion(
            db,
            capture_id,
            ingest_key,
            200,
            payload_size,
            int((datetime.utcnow() - (started_at or datetime.utcnow())).total_seconds() * 1000),
            None,
        )
        return {
            "status": "duplicate",
            "scan_id": str(existing.id),
            "capture_id": capture_id,
            "created": False,
            "message": "Scan already ingested",
        }

    # Upsert device
    device = db.query(Device).filter_by(device_code=device_code).first()
    if not device:
        device = Device(
            device_code=device_code,
            s3_prefix_hint=f"raw/{device_code}/",
            last_upload_at=datetime.utcnow(),
            captures_count=1,
        )
        db.add(device)
    else:
        device.last_upload_at = datetime.utcnow()
        device.captures_count += 1

    db.flush()

    image_asset = None
    mask_asset = None
    backfat_line_asset = None
    image_relpath = meta_json["files"]["image_relpath"]
    mask_relpath = meta_json["files"].get("mask_relpath")
    backfat_line_relpath = meta_json["files"].get("backfat_line_relpath")

    for obj in objects:
        if obj == image_relpath:
            image_asset = Asset(
                bucket=bucket,
                object_key=f"{ingest_key}{obj}",
                sha256=meta_json["image_sha256"],
                mime_type="image/jpeg" if obj.lower().endswith(".jpg") else "image/png",
            )
            db.add(image_asset)
        elif mask_relpath and obj == mask_relpath:
            mask_asset = Asset(
                bucket=bucket,
                object_key=f"{ingest_key}{obj}",
                sha256=meta_json.get("mask_sha256", ""),
                mime_type="image/png",
            )
            db.add(mask_asset)
        elif backfat_line_relpath and obj == backfat_line_relpath:
            backfat_line_asset = Asset(
                bucket=bucket,
                object_key=f"{ingest_key}{obj}",
                sha256=meta_json.get("backfat_line_sha256", ""),
                mime_type="image/png",
            )
            db.add(backfat_line_asset)

    db.flush()

    gps_point = None
    farm_id = None
    if meta_json.get("gps"):
        gps = meta_json["gps"]
        gps_point = ST_SetSRID(ST_MakePoint(gps["lon"], gps["lat"]), 4326)
        farm_id = find_farm_for_point(db, gps_point)

    group_name = meta_json.get("group_name") or group_external_id
    group = get_or_create_group(
        db,
        external_id=group_external_id,
        farm_id=farm_id,
        name_hint=group_name,
    )
    animal = get_or_create_animal(
        db,
        rfid=animal_rfid,
        farm_id=farm_id or (group.farm_id if group else None),
        group=group,
    )
    group_id = group.id if group else None

    scan = Scan(
        capture_id=capture_id,
        ingest_key=ingest_key,
        device_id=device.id,
        captured_at=datetime.fromisoformat(meta_json["captured_at"].replace("Z", "+00:00")),
        status=ScanStatus.ingested,
        image_asset_id=image_asset.id if image_asset else None,
        mask_asset_id=mask_asset.id if mask_asset else None,
        backfat_line_asset_id=backfat_line_asset.id if backfat_line_asset else None,
        gps=gps_point,
        farm_id=farm_id,
        grading=grading,
        meta=meta_json,
        group_id=group_id,
        imf=imf,
        backfat_thickness=backfat_value,
        animal_weight=animal_weight,
        animal_rfid=animal_rfid,
        animal_id=animal.id if animal else None,
        ribeye_area=ribeye_area,
        clarity=ScanQuality(clarity_value) if clarity_value else None,
        usability=ScanQuality(usability_value) if usability_value else None,
        label=label,
    )
    db.add(scan)
    db.flush()

    event = ScanEvent(
        scan_id=scan.id,
        event="ingested",
        meta={
            "source": source,
            "device_code": device_code,
            "objects": objects,
            "firmware": meta_json.get("firmware"),
            "probe": meta_json.get("probe"),
        },
    )
    db.add(event)

    elapsed_ms = int((datetime.utcnow() - (started_at or datetime.utcnow())).total_seconds() * 1000)
    log_ingestion(db, capture_id, ingest_key, 200, payload_size, elapsed_ms, None)

    db.commit()

    return {
        "status": "success",
        "scan_id": str(scan.id),
        "capture_id": capture_id,
        "created": True,
        "message": "Scan ingested successfully",
    }
