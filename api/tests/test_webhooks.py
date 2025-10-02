"""Test webhook ingestion endpoints."""
import pytest
import json
import hmac
import hashlib
from datetime import datetime
from app.models import Device, Scan, Asset, ScanEvent, IngestionLog


def create_hmac_signature(timestamp: str, body: str, secret: str = "dev_secret_change_me") -> str:
    """Create HMAC signature for webhook payload."""
    message = f"{timestamp}.{body}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


@pytest.fixture
def test_device(test_db):
    """Create a test device."""
    db = test_db()
    device = Device(device_code="TEST-DEV-001", label="Test Device")
    db.add(device)
    db.commit()
    db.refresh(device)
    db.close()
    return device


def test_webhook_valid_payload(client, test_device):
    """Webhook accepts valid signed payload."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "ingest_key": f"raw/{test_device.device_code}/2025/01/01/cap_123/",
        "device_code": test_device.device_code,
        "objects": ["image.jpg", "meta.json"],
        "meta_json": {
            "meta_version": "1.0.0",
            "device_code": test_device.device_code,
            "capture_id": "cap_123",
            "captured_at": "2025-01-01T12:00:00Z",
            "image_sha256": "a" * 64,  # Valid SHA256 format
            "files": {
                "image_relpath": "image.jpg"
            },
            "probe": {
                "model": "Test Probe"
            },
            "firmware": {
                "app_version": "1.0.0"
            }
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
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ingested"
    assert "scan_id" in data


def test_webhook_invalid_signature(client, test_device):
    """Webhook rejects invalid signature."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "prefix": f"raw/{test_device.device_code}/2025/01/01/cap_456/",
        "device_code": test_device.device_code,
        "meta": {
            "meta_version": "1.0.0",
            "device_code": test_device.device_code,
            "capture_id": "cap_456",
            "captured_at": "2025-01-01T12:00:00Z",
            "image_sha256": "xyz789",
            "files": {
                "image_relpath": "image.jpg"
            },
            "probe": {
                "model": "Test Probe",
                "serial": "TP-001"
            },
            "firmware": {
                "version": "1.0.0"
            }
        }
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
    assert "Invalid signature" in response.json()["detail"]


def test_webhook_missing_signature(client, test_device):
    """Webhook rejects request without signature."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "prefix": f"raw/{test_device.device_code}/2025/01/01/cap_789/",
        "device_code": test_device.device_code,
        "meta": {}
    }
    
    response = client.post(
        "/ingest/webhook",
        headers={"X-CTI-Timestamp": timestamp},
        json=payload
    )
    
    assert response.status_code == 400


def test_webhook_expired_timestamp(client, test_device):
    """Webhook rejects old timestamps."""
    # Use timestamp from 10 minutes ago (beyond 5 minute window)
    old_timestamp = str(int(datetime.utcnow().timestamp()) - 600)
    payload = {
        "bucket": "test-bucket",
        "prefix": f"raw/{test_device.device_code}/2025/01/01/cap_old/",
        "device_code": test_device.device_code,
        "meta": {
            "meta_version": "1.0.0",
            "device_code": test_device.device_code,
            "capture_id": "cap_old",
            "captured_at": "2025-01-01T12:00:00Z",
            "image_sha256": "old123",
            "files": {
                "image_relpath": "image.jpg"
            },
            "probe": {
                "model": "Test Probe",
                "serial": "TP-001"
            },
            "firmware": {
                "version": "1.0.0"
            }
        }
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
        "prefix": f"raw/{test_device.device_code}/2025/01/01/cap_bad/",
        "device_code": test_device.device_code,
        "meta": {
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
    assert "schema" in response.json()["detail"].lower()


def test_webhook_unknown_device(client):
    """Webhook rejects unknown device code."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "prefix": "raw/UNKNOWN-DEV/2025/01/01/cap_unk/",
        "device_code": "UNKNOWN-DEV",
        "meta": {
            "meta_version": "1.0.0",
            "device_code": "UNKNOWN-DEV",
            "capture_id": "cap_unk",
            "captured_at": "2025-01-01T12:00:00Z",
            "image_sha256": "unk123",
            "files": {
                "image_relpath": "image.jpg"
            },
            "probe": {
                "model": "Test Probe",
                "serial": "TP-001"
            },
            "firmware": {
                "version": "1.0.0"
            }
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
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_webhook_idempotency(client, test_device):
    """Webhook is idempotent - same payload returns existing scan."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "prefix": f"raw/{test_device.device_code}/2025/01/01/cap_idem/",
        "device_code": test_device.device_code,
        "meta": {
            "meta_version": "1.0.0",
            "device_code": test_device.device_code,
            "capture_id": "cap_idem",
            "captured_at": "2025-01-01T12:00:00Z",
            "image_sha256": "idem123",
            "files": {
                "image_relpath": "image.jpg"
            },
            "probe": {
                "model": "Test Probe",
                "serial": "TP-001"
            },
            "firmware": {
                "version": "1.0.0"
            }
        }
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
    
    # Second request with same payload (new timestamp and signature)
    timestamp2 = str(int(datetime.utcnow().timestamp()))
    signature2 = create_hmac_signature(timestamp2, body)
    headers2 = {
        "X-CTI-Timestamp": timestamp2,
        "X-CTI-Signature": signature2
    }
    
    response2 = client.post("/ingest/webhook", headers=headers2, json=payload)
    assert response2.status_code == 200
    scan_id_2 = response2.json()["scan_id"]
    
    # Should return same scan
    assert scan_id_1 == scan_id_2


def test_webhook_with_mask(client, test_device):
    """Webhook accepts payload with mask file."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "prefix": f"raw/{test_device.device_code}/2025/01/01/cap_mask/",
        "device_code": test_device.device_code,
        "meta": {
            "meta_version": "1.0.0",
            "device_code": test_device.device_code,
            "capture_id": "cap_mask",
            "captured_at": "2025-01-01T12:00:00Z",
            "image_sha256": "img123",
            "mask_sha256": "mask123",
            "files": {
                "image_relpath": "image.jpg",
                "mask_relpath": "mask.png"
            },
            "probe": {
                "model": "Test Probe",
                "serial": "TP-001"
            },
            "firmware": {
                "version": "1.0.0"
            }
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
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ingested"


def test_webhook_with_gps(client, test_device):
    """Webhook accepts payload with GPS coordinates."""
    timestamp = str(int(datetime.utcnow().timestamp()))
    payload = {
        "bucket": "test-bucket",
        "prefix": f"raw/{test_device.device_code}/2025/01/01/cap_gps/",
        "device_code": test_device.device_code,
        "meta": {
            "meta_version": "1.0.0",
            "device_code": test_device.device_code,
            "capture_id": "cap_gps",
            "captured_at": "2025-01-01T12:00:00Z",
            "image_sha256": "gps123",
            "files": {
                "image_relpath": "image.jpg"
            },
            "gps": {
                "lat": 45.5,
                "lon": -73.6
            },
            "probe": {
                "model": "Test Probe",
                "serial": "TP-001"
            },
            "firmware": {
                "version": "1.0.0"
            }
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
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ingested"
