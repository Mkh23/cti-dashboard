#!/usr/bin/env python3
import os, json, time, datetime, hashlib, tempfile, pathlib, boto3

BUCKET = os.environ.get("CTI_BUCKET", "cti-dev-406214277746")
REGION = os.environ.get("AWS_REGION", "ca-central-1")
DEVICE = os.environ.get("CTI_DEVICE", "dev-smoke-123")

def tiny_bytes(kind):
    if kind == "jpg":
        return b"\xff\xd8\xff\xd9"  # minimal marker-only JPEG, fine for smoke
    if kind == "png":
        return bytes.fromhex("89504e470d0a1a0a0000000049454e44ae426082")
    raise ValueError

def sha256(b): return hashlib.sha256(b).hexdigest()

def main():
    # at the top of main(), replace the client construction:
    PROFILE = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE")
    print("Using profile:", PROFILE, "region:", REGION)
    session = boto3.Session(profile_name=PROFILE, region_name=REGION) if PROFILE else boto3.Session(region_name=REGION)
    s3 = session.client("s3")
    # s3 = boto3.client("s3", region_name=REGION)
    epoch = int(time.time())
    cap_id = f"cap_{epoch}"
    dt = datetime.datetime.utcfromtimestamp(epoch)
    prefix = f"raw/{DEVICE}/{dt:%Y/%m/%d}/{cap_id}/"

    img = tiny_bytes("jpg")
    msk = tiny_bytes("png")
    meta = {
        "meta_version":"1.0.0",
        "device_code":DEVICE,
        "capture_id":cap_id,
        "captured_at":dt.replace(microsecond=0).isoformat()+"Z",
        "files":{"image_relpath":"image.jpg","mask_relpath":"mask.png"},
        "image_sha256":sha256(img),
        "mask_sha256":sha256(msk),
        "probe":{"model":"linear-5-10"},
        "firmware":{"app_version":"rpi-ultra-0.1.0"}
    }

    with tempfile.TemporaryDirectory() as td:
        td = pathlib.Path(td)
        (td/"image.jpg").write_bytes(img)
        (td/"mask.png").write_bytes(msk)
        (td/"meta.json").write_text(json.dumps(meta, separators=(",",":")))
        s3.put_object(Bucket=BUCKET, Key=prefix+"image.jpg", Body=img, ContentType="image/jpeg")
        s3.put_object(Bucket=BUCKET, Key=prefix+"mask.png",  Body=msk, ContentType="image/png")
        s3.put_object(Bucket=BUCKET, Key=prefix+"meta.json", Body=json.dumps(meta).encode(), ContentType="application/json")
    print("Uploaded:", f"s3://{BUCKET}/{prefix}(image.jpg, mask.png, meta.json)")

if __name__ == "__main__":
    main()
