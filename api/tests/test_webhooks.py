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


def create_valid_meta_json(capture_id: str, device_code: str) -> dict:
    """Create a valid meta.json payload."""
    return {
        "meta_version": "1.0.0",
        "device_code": device_code,
        "capture_id": capture_id,
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
    
    # Second request with same payload (new timestamp and signature)
    import time
    time.sleep(2)  # Ensure different timestamp
    # Use current time to avoid timing issues
    timestamp2 = str(int(time.time()))
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
