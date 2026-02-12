import os, json, hmac, hashlib, time, requests

API_URL = os.environ.get("INGEST_WEBHOOK_URL", "http://localhost:8000/ingest/webhook")
SECRET  = os.environ.get("HMAC_SECRET", "dev_secret_change_me")

def sign(ts: str, body: bytes) -> str:
    return hmac.new(SECRET.encode(), f"{ts}.{body.decode()}".encode(), hashlib.sha256).hexdigest()

def test_webhook_hmac_ok():
    payload = {
        "event_id": "evt-pytest",
        "bucket": os.environ.get("CTI_BUCKET", "cti-dev-406214277746"),
        "ingest_key": "raw/dev-pytest/2025/10/06/cap_1700000000/meta.json",
        "device_code": "dev-pytest",
        "meta_json": {
            "meta_version":"1.0.0",
            "device_code":"dev-pytest",
            "capture_id":"cap_1700000000",
            "captured_at":"2025-10-06T16:15:00Z",
            "files":{"image_relpath":"image.jpg","mask_relpath":"mask.png","backfat_line_relpath":"backfat_line.png"},
            "image_sha256":"0"*64,
            "mask_sha256":"1"*64,
            "backfat_line_sha256":"2"*64,
            "probe":{"model":"linear-5-10"},
            "firmware":{"app_version":"rpi-ultra-0.1.0"}
        },
        "etag":"abc123","size_bytes":123,"event_time":"2025-10-06T16:15:05Z"
    }
    body = json.dumps(payload, separators=(",",":")).encode()
    ts = str(int(time.time()))
    sig = sign(ts, body)
    headers = {
        "Content-Type":"application/json",
        "X-CTI-Timestamp": ts,
        "X-CTI-Signature": f"sha256={sig}",
    }
    r = requests.post(API_URL, headers=headers, data=body, timeout=10)
    assert r.status_code in (200, 409, 200)  # 200 or duplicate behavior
