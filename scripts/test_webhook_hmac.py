#!/usr/bin/env python3
import os, json, hmac, hashlib, time, requests, sys

API_URL = os.environ.get("INGEST_WEBHOOK_URL", "http://localhost:8000/ingest/webhook")
SECRET  = os.environ.get("HMAC_SECRET", "dev_secret_change_me")

def main():
    payload = {
        "event_id": "evt-local-test",
        "bucket": "cti-dev-406214277746",
        "ingest_key": "raw/dev-local/2025/10/06/cap_1700000000/meta.json",
        "device_code": "dev-local",
        "meta_json": {
            "meta_version": "1.0.0",
            "device_code": "dev-local",
            "capture_id": "cap_1700000000",
            "captured_at": "2025-10-06T16:15:00Z",
            "files": {"image_relpath": "image.jpg", "mask_relpath": "mask.png"},
            "image_sha256": "0"*64,
            "mask_sha256": "1"*64,
            "probe": {"model":"linear-5-10"},
            "firmware": {"app_version":"rpi-ultra-0.1.0"}
        },
        "etag": "abc123",
        "size_bytes": 123,
        "event_time": "2025-10-06T16:15:05Z"
    }
    body = json.dumps(payload, separators=(",",":")).encode()
    ts = str(int(time.time()))
    sig = hmac.new(SECRET.encode(), f"{ts}.{body.decode()}".encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-CTI-Timestamp": ts,
        "X-CTI-Signature": f"sha256={sig}",
    }
    r = requests.post(API_URL, headers=headers, data=body, timeout=8)
    print("HTTP", r.status_code, r.text)
    sys.exit(0 if r.ok else 1)

if __name__ == "__main__":
    main()
