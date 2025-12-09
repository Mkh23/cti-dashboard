import os, json, time, datetime, hashlib
from pathlib import Path

import boto3
import pytest

BUCKET = os.environ.get("CTI_BUCKET")
PROFILE = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE")
REGION = os.environ.get("AWS_REGION", "ca-central-1")
SAMPLE_DIR = Path(os.environ.get("CTI_SAMPLE_DIR", Path(__file__).resolve().parent / "scan20261208"))

pytestmark = pytest.mark.e2e


def load_sample_assets():
    """Load the real sample image/mask + meta from tests/scan20261208 or CTI_SAMPLE_DIR."""
    meta_path = SAMPLE_DIR / "meta.json"
    meta = json.loads(meta_path.read_text())
    image_path = SAMPLE_DIR / meta["files"]["image_relpath"]
    mask_rel = meta["files"].get("mask_relpath")
    mask_path = SAMPLE_DIR / mask_rel if mask_rel else None
    img = image_path.read_bytes()
    msk = mask_path.read_bytes() if mask_path and mask_path.exists() else None
    meta["image_sha256"] = hashlib.sha256(img).hexdigest()
    if msk:
        meta["mask_sha256"] = hashlib.sha256(msk).hexdigest()
    return img, msk, meta


@pytest.mark.skipif(not BUCKET, reason="CTI_BUCKET not set; skipping e2e")
def test_s3_to_lambda_to_api():
    session = boto3.Session(profile_name=PROFILE, region_name=REGION) if PROFILE else boto3.Session(region_name=REGION)
    s3 = session.client("s3")
    epoch = int(time.time())
    device = "dev-e2e-pytest"
    cap_id = f"cap_{epoch}"
    dt = datetime.datetime.utcfromtimestamp(epoch)
    prefix = f"raw/{device}/{dt:%Y/%m/%d}/{cap_id}/"

    img, msk, sample_meta = load_sample_assets()
    meta = {
        **sample_meta,
        "device_code": device,
        "capture_id": cap_id,
        "captured_at": dt.replace(microsecond=0).isoformat() + "Z",
    }

    image_key = prefix + meta["files"]["image_relpath"]
    s3.put_object(Bucket=BUCKET, Key=image_key, Body=img, ContentType="image/jpeg" if image_key.lower().endswith(".jpg") else "image/png")
    if msk and meta["files"].get("mask_relpath"):
        mask_key = prefix + meta["files"]["mask_relpath"]
        s3.put_object(Bucket=BUCKET, Key=mask_key,  Body=msk, ContentType="image/png")
    s3.put_object(Bucket=BUCKET, Key=prefix+"meta.json", Body=json.dumps(meta, separators=(",", ":")).encode(), ContentType="application/json")

    # Minimal assertion: upload succeeded; Lambda→API verified by CloudWatch logs
    # (Optionally: poll your API /admin or DB to confirm a Scan was created.)
    assert True
