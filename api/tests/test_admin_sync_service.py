"""Tests for the admin scan sync service."""
import io
import json

from app.models import Asset, Scan
from app.services import sync_service
from app.services.ingest_service import ingest_scan_from_payload


def _sample_meta(capture_id: str, device_code: str):
    return {
        "meta_version": "1.0.0",
        "device_code": device_code,
        "capture_id": capture_id,
        "captured_at": "2025-01-01T12:00:00Z",
        "image_sha256": "a" * 64,
        "files": {"image_relpath": "image.jpg"},
        "gps": {"lat": 45.0, "lon": -75.0},
        "grading": "auto-seeded",
        "probe": {"model": "SyncProbe"},
        "firmware": {"app_version": "1.0.0"},
    }


class _FakeBody(io.BytesIO):
    def read(self, *args, **kwargs):  # pragma: no cover - wrapper for typing
        return super().read(*args, **kwargs)


class _FakeS3:
    def __init__(self, payloads):
        self.payloads = payloads

    def get_object(self, Bucket, Key):
        return {"Body": _FakeBody(self.payloads[Key])}


def test_sync_scans_add_only(monkeypatch, test_db):
    """S3 sync ingests new scans when missing locally."""
    meta_key = "raw/DEV-001/2025/01/01/cap_1001/meta.json"
    ingest_key = "raw/DEV-001/2025/01/01/cap_1001/"
    meta = _sample_meta("cap_1001", "DEV-001")
    fake_s3 = _FakeS3({meta_key: json.dumps(meta).encode("utf-8")})

    monkeypatch.setattr(
        sync_service,
        "_list_meta_keys",
        lambda s3, bucket, prefix: [meta_key],
    )
    monkeypatch.setattr(
        sync_service,
        "_list_objects_in_capture",
        lambda s3, bucket, prefix: ["image.jpg", "meta.json"],
    )

    session = test_db()
    try:
        result = sync_service.sync_scans_from_bucket(
            session,
            bucket="test-bucket",
            prefix="raw/",
            mode="add_only",
            s3_client=fake_s3,
        )
        assert result["added"] == 1
        assert result["duplicates"] == 0
        assert result["removed"] == 0
        assert result["synced_ingest_keys"] == 1

        scan = session.query(Scan).filter(Scan.ingest_key == ingest_key).one()
        assert scan.capture_id == "cap_1001"
    finally:
        session.close()


def test_sync_scans_add_remove_drops_missing(monkeypatch, test_db):
    """Mirror mode removes scans that no longer exist in S3."""
    new_meta_key = "raw/DEV-NEW/2025/01/01/cap_2002/meta.json"
    new_ingest = "raw/DEV-NEW/2025/01/01/cap_2002/"
    new_meta = _sample_meta("cap_2002", "DEV-NEW")
    fake_s3 = _FakeS3({new_meta_key: json.dumps(new_meta).encode("utf-8")})

    monkeypatch.setattr(
        sync_service,
        "_list_meta_keys",
        lambda s3, bucket, prefix: [new_meta_key],
    )
    monkeypatch.setattr(
        sync_service,
        "_list_objects_in_capture",
        lambda s3, bucket, prefix: ["image.jpg", "meta.json"],
    )

    session = test_db()
    try:
        # Seed an existing scan that should be removed.
        old_meta = _sample_meta("cap_3003", "DEV-OLD")
        ingest_scan_from_payload(
            session,
            bucket="test-bucket",
            ingest_key="raw/DEV-OLD/2024/12/31/cap_3003/",
            device_code="DEV-OLD",
            objects=["image.jpg", "meta.json"],
            meta_json=old_meta,
            source="seed",
            payload_size=len(json.dumps(old_meta)),
        )

        result = sync_service.sync_scans_from_bucket(
            session,
            bucket="test-bucket",
            prefix="raw/",
            mode="add_remove",
            s3_client=fake_s3,
        )

        assert result["added"] == 1
        assert result["removed"] == 1
        scans = session.query(Scan).all()
        assert len(scans) == 1
        assert scans[0].ingest_key == new_ingest
        # Old assets should be gone (only one from new ingest remains).
        assert session.query(Asset).count() == 1
    finally:
        session.close()
