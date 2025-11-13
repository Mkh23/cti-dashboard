import pytest

from app.services.sync_service import _apply_ingest_defaults


def test_apply_ingest_defaults_backfills_required_fields():
    meta = {
        "captureId": "scan202510031320",
        "capturedAtIso": "2025-10-03T19:20:45Z",
        "deviceId": "dev-0001",
        "meta_version": "1",
    }
    ingest_key = "raw/dev-0001/2025/10/03/scan202510031320/"
    objects = ["image.jpg", "mask.png"]

    normalized = _apply_ingest_defaults(meta, ingest_key=ingest_key, objects=objects)

    assert normalized["meta_version"] == "1.0.0"
    assert normalized["capture_id"] == "cap_202510031320"
    assert normalized["captured_at"] == "2025-10-03T19:20:45Z"
    assert normalized["device_code"] == "dev-0001"
    assert normalized["files"]["image_relpath"] == "image.jpg"
    assert normalized["probe"]["model"] == "unknown-probe"
    assert normalized["firmware"]["app_version"] == "0.0.0"
    assert len(normalized["image_sha256"]) == 64
    assert normalized["clarity"] == "bad"
    assert normalized["IMF"] == 0


def test_apply_ingest_defaults_generates_capture_id_from_ingest_key():
    meta = {}
    ingest_key = "raw/dev-123/2025/01/02/cap_123456789/"
    objects = ["foo.jpg"]

    normalized = _apply_ingest_defaults(meta, ingest_key=ingest_key, objects=objects)

    assert normalized["capture_id"] == "cap_123456789"
    assert normalized["files"]["image_relpath"] == "foo.jpg"
