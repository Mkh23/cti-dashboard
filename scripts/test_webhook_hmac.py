#!/usr/bin/env python3
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

API_URL = os.environ.get("INGEST_WEBHOOK_URL", "http://157.90.181.99:10001/ingest/webhook")
SECRET = os.environ.get("HMAC_SECRET", "e3f03e0bbf9cb5262659352c9f949d572fd911830ba2de497ccf0d0734ec57e1")
SAMPLE_DIR = Path(os.environ.get("CTI_SAMPLE_DIR", Path(__file__).resolve().parents[1] / "tests" / "scan20261208"))


def load_sample_assets():
    meta_path = SAMPLE_DIR / "meta.json"
    meta = json.loads(meta_path.read_text())
    image_path = SAMPLE_DIR / meta["files"]["image_relpath"]
    mask_rel = meta["files"].get("mask_relpath")
    mask_path = SAMPLE_DIR / mask_rel if mask_rel else None
    img = image_path.read_bytes()
    mask = mask_path.read_bytes() if mask_path and mask_path.exists() else None
    meta["image_sha256"] = hashlib.sha256(img).hexdigest()
    if mask:
        meta["mask_sha256"] = hashlib.sha256(mask).hexdigest()
    return img, mask, meta


def maybe_upload_to_s3(bucket: str, ingest_key: str, img: bytes, mask: Optional[bytes], meta: dict):
    if not os.environ.get("UPLOAD_TO_S3"):
        return

    try:
        import boto3  # type: ignore
    except ImportError:
        print("UPLOAD_TO_S3=1 set but boto3 is not installed; skipping S3 upload.", file=sys.stderr)
        return

    profile = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE")
    region = os.environ.get("AWS_REGION", "ca-central-1")
    session = boto3.Session(profile_name=profile, region_name=region) if profile else boto3.Session(region_name=region)
    s3 = session.client("s3")
    image_key = ingest_key + meta["files"]["image_relpath"]
    s3.put_object(Bucket=bucket, Key=image_key, Body=img, ContentType="image/jpeg" if image_key.lower().endswith(".jpg") else "image/png")
    if mask and meta["files"].get("mask_relpath"):
        s3.put_object(
            Bucket=bucket,
            Key=ingest_key + meta["files"]["mask_relpath"],
            Body=mask,
            ContentType="image/png",
        )
    s3.put_object(
        Bucket=bucket,
        Key=f"{ingest_key}meta.json",
        Body=json.dumps(meta, separators=(",", ":")).encode(),
        ContentType="application/json",
    )
    file_list = [meta["files"]["image_relpath"]]
    if meta["files"].get("mask_relpath"):
        file_list.append(meta["files"]["mask_relpath"])
    print(f"Uploaded sample assets to s3://{bucket}/{ingest_key}({', '.join(file_list)}, meta.json)")


def main():
    device_code = os.environ.get("CTI_DEVICE_CODE", "dev-local")
    bucket = os.environ.get("CTI_BUCKET", "cti-dev-406214277746")
    img, mask, sample_meta = load_sample_assets()
    epoch = int(time.time())
    cap_id = f"cap_{epoch}"
    dt = datetime.utcfromtimestamp(epoch)
    ingest_key = f"raw/{device_code}/{dt:%Y/%m/%d}/{cap_id}/"

    meta = {
        **sample_meta,
        "device_code": device_code,
        "capture_id": cap_id,
        "captured_at": dt.replace(microsecond=0).isoformat() + "Z",
    }

    objects = [meta["files"]["image_relpath"]]
    if meta["files"].get("mask_relpath"):
        objects.append(meta["files"]["mask_relpath"])
    objects.append("meta.json")

    payload = {
        "event_id": f"evt-{cap_id}",
        "bucket": bucket,
        "ingest_key": ingest_key,
        "device_code": device_code,
        "objects": objects,
        "meta_json": meta,
        "etag": "abc123",
        "size_bytes": len(img) + (len(mask) if mask else 0),
        "event_time": dt.replace(microsecond=0).isoformat() + "Z",
    }

    maybe_upload_to_s3(bucket, ingest_key, img, mask, meta)

    body = json.dumps(payload, separators=(",", ":")).encode()
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
