#!/usr/bin/env python3
import datetime
import hashlib
import json
import os
import pathlib
import tempfile
import time

import boto3

BUCKET = os.environ.get("CTI_BUCKET", "cti-dev-406214277746")
REGION = os.environ.get("AWS_REGION", "ca-central-1")
DEVICE = os.environ.get("CTI_DEVICE", "dev-smoke-123")
SAMPLE_DIR = pathlib.Path(os.environ.get("CTI_SAMPLE_DIR", pathlib.Path(__file__).resolve().parents[1] / "tests" / "scan20261208"))


def sha256(b): return hashlib.sha256(b).hexdigest()


def load_sample_assets():
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

    meta["image_sha256"] = sha256(img)
    if mask:
        meta["mask_sha256"] = sha256(mask)
    if backfat:
        meta["backfat_line_sha256"] = sha256(backfat)
    return img, mask, backfat, meta

def main():
    PROFILE = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE")
    print("Using profile:", PROFILE, "region:", REGION)
    session = boto3.Session(profile_name=PROFILE, region_name=REGION) if PROFILE else boto3.Session(region_name=REGION)
    s3 = session.client("s3")
    # s3 = boto3.client("s3", region_name=REGION)
    epoch = int(time.time())
    cap_id = f"cap_{epoch}"
    dt = datetime.datetime.utcfromtimestamp(epoch)
    prefix = f"raw/{DEVICE}/{dt:%Y/%m/%d}/{cap_id}/"

    img, msk, backfat, sample_meta = load_sample_assets()
    meta = {
        **sample_meta,
        "device_code": DEVICE,
        "capture_id": cap_id,
        "captured_at": dt.replace(microsecond=0).isoformat() + "Z",
    }

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        image_name = meta["files"]["image_relpath"]
        mask_name = meta["files"].get("mask_relpath")
        backfat_name = meta["files"].get("backfat_line_relpath")
        (td / image_name).write_bytes(img)
        if msk and mask_name:
            (td / mask_name).write_bytes(msk)
        if backfat and backfat_name:
            (td / backfat_name).write_bytes(backfat)
        (td/"meta.json").write_text(json.dumps(meta, separators=(",",":")))
        image_key = prefix + image_name
        s3.put_object(Bucket=BUCKET, Key=image_key, Body=img, ContentType="image/jpeg" if image_key.lower().endswith(".jpg") else "image/png")
        if msk and mask_name:
            mask_key = prefix + mask_name
            s3.put_object(Bucket=BUCKET, Key=mask_key,  Body=msk, ContentType="image/png")
        if backfat and backfat_name:
            backfat_key = prefix + backfat_name
            s3.put_object(Bucket=BUCKET, Key=backfat_key, Body=backfat, ContentType="image/png")
        s3.put_object(Bucket=BUCKET, Key=prefix+"meta.json", Body=json.dumps(meta).encode(), ContentType="application/json")
    print(
        "Uploaded:",
        f"s3://{BUCKET}/{prefix}({meta['files']['image_relpath']}, {meta['files'].get('mask_relpath')}, {meta['files'].get('backfat_line_relpath')}, meta.json)",
    )

if __name__ == "__main__":
    main()
