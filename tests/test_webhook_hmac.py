import os, json, hmac, hashlib, time
from datetime import datetime
from pathlib import Path

import requests

API_URL = os.environ.get("INGEST_WEBHOOK_URL", "http://localhost:8000/ingest/webhook")
SECRET  = os.environ.get("HMAC_SECRET", "dev_secret_change_me")
SAMPLE_DIR = Path(os.environ.get("CTI_SAMPLE_DIR", Path(__file__).resolve().parent / "scan20261208"))


def load_sample_payload():
    meta_path = SAMPLE_DIR / "meta.json"
    meta = json.loads(meta_path.read_text())
    image_path = SAMPLE_DIR / meta["files"]["image_relpath"]
    mask_rel = meta["files"].get("mask_relpath")
    mask_path = SAMPLE_DIR / mask_rel if mask_rel else None
    backfat_rel = meta["files"].get("backfat_line_relpath")
    backfat_path = SAMPLE_DIR / backfat_rel if backfat_rel else None
    img = image_path.read_bytes()
    mask = mask_path.read_bytes() if mask_path and mask_path.exists() else None
    backfat = backfat_path.read_bytes() if backfat_path and backfat_path.exists() else None
    meta["image_sha256"] = hashlib.sha256(img).hexdigest()
    if mask:
        meta["mask_sha256"] = hashlib.sha256(mask).hexdigest()
    if backfat:
        meta["backfat_line_sha256"] = hashlib.sha256(backfat).hexdigest()
    return img, mask, backfat, meta

def sign(ts: str, body: bytes) -> str:
    return hmac.new(SECRET.encode(), f"{ts}.{body.decode()}".encode(), hashlib.sha256).hexdigest()

def test_webhook_hmac_ok():
    device_code = os.environ.get("CTI_DEVICE_CODE", "dev-pytest")
    bucket = os.environ.get("CTI_BUCKET", "cti-dev-406214277746")
    img, mask, backfat, meta_template = load_sample_payload()
    epoch = int(time.time())
    cap_id = f"cap_{epoch}"
    dt = datetime.utcfromtimestamp(epoch)
    ingest_key = f"raw/{device_code}/{dt:%Y/%m/%d}/{cap_id}/"

    objects = [meta_template["files"]["image_relpath"]]
    if meta_template["files"].get("mask_relpath"):
        objects.append(meta_template["files"]["mask_relpath"])
    if meta_template["files"].get("backfat_line_relpath"):
        objects.append(meta_template["files"]["backfat_line_relpath"])
    objects.append("meta.json")

    payload = {
        "event_id": f"evt-{cap_id}",
        "bucket": bucket,
        "ingest_key": ingest_key,
        "device_code": device_code,
        "objects": objects,
        "meta_json": {
            **meta_template,
            "device_code": device_code,
            "capture_id": cap_id,
            "captured_at": dt.replace(microsecond=0).isoformat() + "Z",
        },
        "etag": "abc123",
        "size_bytes": len(img) + (len(mask) if mask else 0) + (len(backfat) if backfat else 0),
        "event_time": dt.replace(microsecond=0).isoformat() + "Z",
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
