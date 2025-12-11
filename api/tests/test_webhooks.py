"""Test webhook ingestion endpoints."""
import base64
import json
import hmac
import hashlib
import time
from datetime import datetime
from pathlib import Path

import pytest
from geoalchemy2 import WKTElement

from app.models import Asset, Device, Scan, Farm, FarmGeofence, Group


def create_hmac_signature(timestamp: str, body: str, secret: str = "dev_secret_change_me") -> str:
    """Create HMAC signature for webhook payload."""
    message = f"{timestamp}.{body}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def create_valid_meta_json(capture_id: str, device_code: str) -> dict:
    """Create a valid meta.json payload."""
    return {
        "meta_version": "1.0.0",
        "device_code": device_code,
        "capture_id": capture_id,
        "captured_at": "2025-01-01T12:00:00Z",
        "image_sha256": "a" * 64,
        "files": {"image_relpath": "image.jpg"},
        "gps": {"lat": 45.0, "lon": -75.0},
        "grading": "auto-seeded",
        "IMF": "0.92",
        "backfat_thickness": 0.8,
        "animal_weight": 1234.5,
        "Animal_RFID": "RFID-123",
        "group_ID": "HERD-001",
        "ribeye_area": 78.4,
        "clarity": "Good",
        "usability": "medium",
        "label": "Review later",
        "probe": {"model": "Test Probe"},
        "firmware": {"app_version": "1.0.0"},
    }


@pytest.fixture
def test_device(test_db):
    """Create a test device."""
    db = test_db()
    try:
        device = Device(device_code="TEST-DEV-001", label="Test Device")
        db.add(device)
        db.commit()
        db.refresh(device)
        return device
    finally:
        db.close()


def test_webhook_valid_payload(client, test_device, test_db):
    """Webhook accepts valid signed payload."""
    # ensure group exists for assignment
    db = test_db()
    try:
        herd = Group(name="Existing Herd", external_id="HERD-001")
        db.add(herd)
        db.commit()
        db.refresh(herd)
        group_id = herd.id
    finally:
        db.close()

    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/01/01/cap_123/",
        "device_code": test_device.device_code,
        "objects": ["image.jpg", "meta.json"],
        "meta_json": create_valid_meta_json("cap_123", test_device.device_code)
    }
    
    body = json.dumps(payload)
    signature = create_hmac_signature(timestamp, body)
    
    response = client.post(
        "/ingest/webhook",
        headers={
            "X-CTI-Timestamp": timestamp,
            "X-CTI-Signature": signature
        },
        json=payload
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "scan_id" in data

    db = test_db()
    try:
        scan = db.query(Scan).filter(Scan.capture_id == "cap_123").one()
        assert scan.grading == "auto-seeded"
        assert scan.meta is not None
        assert scan.meta["capture_id"] == "cap_123"
        assert scan.imf is not None
        assert float(scan.imf) == pytest.approx(0.92)
        assert scan.backfat_thickness is not None
        assert float(scan.backfat_thickness) == pytest.approx(0.8)
        assert scan.animal_weight is not None
        assert float(scan.animal_weight) == pytest.approx(1234.5)
        assert scan.animal_rfid == "RFID-123"
        assert scan.group_id == group_id
        assert scan.ribeye_area is not None
        assert float(scan.ribeye_area) == pytest.approx(78.4)
        assert scan.clarity.value == "good"
        assert scan.usability.value == "medium"
        assert scan.label == "Review later"
    finally:
        db.close()


def test_webhook_invalid_signature(client, test_device):
    """Webhook rejects invalid signature."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/01/01/cap_456/",
        "device_code": test_device.device_code,
        "objects": ["image.jpg", "meta.json"],
        "meta_json": create_valid_meta_json("cap_456", test_device.device_code)
    }
    
    response = client.post(
        "/ingest/webhook",
        headers={
            "X-CTI-Timestamp": timestamp,
            "X-CTI-Signature": "sha256=invalid_signature"
        },
        json=payload
    )
    
    assert response.status_code == 403
    assert "signature" in response.json()["detail"].lower()


def test_webhook_missing_signature(client, test_device):
    """Webhook rejects request without signature."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/01/01/cap_789/",
        "device_code": test_device.device_code,
        "objects": ["image.jpg", "meta.json"],
        "meta_json": create_valid_meta_json("cap_789", test_device.device_code)
    }
    
    response = client.post(
        "/ingest/webhook",
        headers={"X-CTI-Timestamp": timestamp},
        json=payload
    )
    
    assert response.status_code == 401


def test_webhook_expired_timestamp(client, test_device):
    """Webhook rejects old timestamps."""
    # Use timestamp from 10 minutes ago (beyond 5 minute window)
    old_timestamp = str(int(datetime.utcnow().timestamp()) - 600)
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/01/01/cap_old/",
        "device_code": test_device.device_code,
        "objects": ["image.jpg", "meta.json"],
        "meta_json": create_valid_meta_json("cap_old", test_device.device_code)
    }
    
    body = json.dumps(payload)
    signature = create_hmac_signature(old_timestamp, body)
    
    response = client.post(
        "/ingest/webhook",
        headers={
            "X-CTI-Timestamp": old_timestamp,
            "X-CTI-Signature": signature
        },
        json=payload
    )
    
    assert response.status_code == 403
    assert "signature" in response.json()["detail"].lower()


def test_webhook_invalid_meta_schema(client, test_device):
    """Webhook rejects invalid meta.json schema."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/01/01/cap_bad/",
        "device_code": test_device.device_code,
        "objects": ["image.jpg", "meta.json"],
        "meta_json": {
            "meta_version": "1.0.0",
            # Missing required fields
            "device_code": test_device.device_code
        }
    }
    
    body = json.dumps(payload)
    signature = create_hmac_signature(timestamp, body)
    
    response = client.post(
        "/ingest/webhook",
        headers={
            "X-CTI-Timestamp": timestamp,
            "X-CTI-Signature": signature
        },
        json=payload
    )
    
    assert response.status_code == 400
    assert "validation" in response.json()["detail"].lower() or "required" in response.json()["detail"].lower()


def test_webhook_idempotency(client, test_device):
    """Webhook is idempotent - same payload returns existing scan."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/01/01/cap_999888/",
        "device_code": test_device.device_code,
        "objects": ["image.jpg", "meta.json"],
        "meta_json": create_valid_meta_json("cap_999888", test_device.device_code)
    }
    
    body = json.dumps(payload)
    signature = create_hmac_signature(timestamp, body)
    headers = {
        "X-CTI-Timestamp": timestamp,
        "X-CTI-Signature": signature
    }
    
    # First request
    response1 = client.post("/ingest/webhook", headers=headers, json=payload)
    assert response1.status_code == 200
    scan_id_1 = response1.json()["scan_id"]
    
    # Second request with same payload (new signature)
    timestamp2 = timestamp
    signature2 = create_hmac_signature(timestamp2, body)
    headers2 = {
        "X-CTI-Timestamp": timestamp2,
        "X-CTI-Signature": signature2,
        "Content-Type": "application/json"
    }
    
    # Use raw body content for second request to ensure exact signature match
    response2 = client.post("/ingest/webhook", headers=headers2, content=body)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "duplicate"
    scan_id_2 = data2["scan_id"]
    
    # Should return same scan
    assert scan_id_1 == scan_id_2


def test_webhook_assigns_farm_from_geofence(client, test_device, test_db):
    """Webhook assigns farm based on geofence polygons."""
    db = test_db()
    try:
        farm = Farm(name="Polygon Farm")
        db.add(farm)
        db.flush()

        geofence = FarmGeofence(
            farm_id=farm.id,
            label="Primary boundary",
            geometry=WKTElement(
                "POLYGON((-75.2 44.8, -74.8 44.8, -74.8 45.2, -75.2 45.2, -75.2 44.8))",
                srid=4326,
            ),
        )
        db.add(geofence)
        db.commit()
        farm_id = farm.id
    finally:
        db.close()

    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/01/01/cap_777001/",
        "device_code": test_device.device_code,
        "objects": ["image.jpg", "meta.json"],
        "meta_json": create_valid_meta_json("cap_777001", test_device.device_code),
    }
    body = json.dumps(payload)
    signature = create_hmac_signature(timestamp, body)

    response = client.post(
        "/ingest/webhook",
        headers={"X-CTI-Timestamp": timestamp, "X-CTI-Signature": signature},
        json=payload,
    )
    assert response.status_code == 200

    db = test_db()
    try:
        scan = db.query(Scan).filter(Scan.capture_id == "cap_777001").one()
        assert scan.farm_id == farm_id
        assert scan.meta["gps"]["lat"] == 45.0
    finally:
        db.close()


def load_sample_payload():
    """Load shared image/mask + meta defaults used for E2E ingest tests."""
    fixture = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "sample_ingest_payload.json"
    payload = json.loads(fixture.read_text())
    img = base64.b64decode(payload["image_png_base64"])
    mask = base64.b64decode(payload["mask_png_base64"])
    defaults = payload["meta_defaults"]
    return img, mask, defaults


def test_webhook_ingests_full_payload_with_mask_and_metrics(client, test_device, test_db):
    """Webhook accepts the canonical sample with real image/mask hashes and persists mask asset + metrics."""
    img, mask, defaults = load_sample_payload()
    capture_id = "cap_full_payload"
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/12/01/{capture_id}/",
        "device_code": test_device.device_code,
        "objects": ["image.png", "mask.png", "meta.json"],
        "meta_json": {
            "meta_version": "1.0.0",
            "device_code": test_device.device_code,
            "capture_id": capture_id,
            "captured_at": "2025-12-01T15:04:05Z",
            "image_sha256": hashlib.sha256(img).hexdigest(),
            "mask_sha256": hashlib.sha256(mask).hexdigest(),
            **defaults,
        },
        "etag": "abc123",
        "size_bytes": len(img) + len(mask),
        "event_time": "2025-12-01T15:04:10Z",
    }
    body = json.dumps(payload)
    signature = create_hmac_signature(timestamp, body)

    response = client.post(
        "/ingest/webhook",
        headers={"X-CTI-Timestamp": timestamp, "X-CTI-Signature": signature},
        json=payload,
    )
    assert response.status_code == 200

    db = test_db()
    try:
        scan = db.query(Scan).filter(Scan.capture_id == capture_id).one()
        assert scan.mask_asset_id is not None
        assert scan.meta["files"]["mask_relpath"] == "mask.png"
        assert scan.imf is not None
        assert float(scan.backfat_thickness) == pytest.approx(0.85)
        assert scan.clarity.value == "good"
        mask_asset = db.query(Asset).filter(Asset.id == scan.mask_asset_id).one()
        assert mask_asset.sha256 == hashlib.sha256(mask).hexdigest()
    finally:
        db.close()
