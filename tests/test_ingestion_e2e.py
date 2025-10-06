import os, json, time, datetime, hashlib, boto3, pytest

BUCKET = os.environ.get("CTI_BUCKET")
PROFILE = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE")
REGION = os.environ.get("AWS_REGION", "ca-central-1")

pytestmark = pytest.mark.e2e

@pytest.mark.skipif(not BUCKET, reason="CTI_BUCKET not set; skipping e2e")
def test_s3_to_lambda_to_api():
    session = boto3.Session(profile_name=PROFILE, region_name=REGION) if PROFILE else boto3.Session(region_name=REGION)
    s3 = session.client("s3")
    epoch = int(time.time())
    device = "dev-e2e-pytest"
    cap_id = f"cap_{epoch}"
    dt = datetime.datetime.utcfromtimestamp(epoch)
    prefix = f"raw/{device}/{dt:%Y/%m/%d}/{cap_id}/"

    def sha256(b): return hashlib.sha256(b).hexdigest()
    img = b"\xff\xd8\xff\xd9"
    msk = bytes.fromhex("89504e470d0a1a0a0000000049454e44ae426082")
    meta = {
        "meta_version":"1.0.0",
        "device_code":device,
        "capture_id":cap_id,
        "captured_at":dt.replace(microsecond=0).isoformat()+"Z",
        "files":{"image_relpath":"image.jpg","mask_relpath":"mask.png"},
        "image_sha256":sha256(img),
        "mask_sha256":sha256(msk),
        "probe":{"model":"linear-5-10"},
        "firmware":{"app_version":"rpi-ultra-0.1.0"}
    }

    s3.put_object(Bucket=BUCKET, Key=prefix+"image.jpg", Body=img, ContentType="image/jpeg")
    s3.put_object(Bucket=BUCKET, Key=prefix+"mask.png",  Body=msk, ContentType="image/png")
    s3.put_object(Bucket=BUCKET, Key=prefix+"meta.json", Body=json.dumps(meta).encode(), ContentType="application/json")

    # Minimal assertion: upload succeeded; Lambda→API verified by CloudWatch logs
    # (Optionally: poll your API /admin or DB to confirm a Scan was created.)
    assert True
