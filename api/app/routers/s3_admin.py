# api/app/routers/s3_admin.py
import os
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from botocore.exceptions import ClientError

# absolute import because s3_utils is at app/s3_utils.py
from app.s3_utils import get_s3_client, generate_presigned_url

BUCKET  = os.getenv("CTI_BUCKET", "cti-dev-406214277746")
KMS_KEY = os.getenv("CTI_KMS_KEY_ID")  # arn:aws:kms:...

router = APIRouter(prefix="/admin/s3", tags=["S3 Admin"])

@router.get("/list")
def list_objects(prefix: str = "", max_keys: int = 200, continuation_token: Optional[str] = None):
    s3 = get_s3_client()
    try:
        kwargs = dict(Bucket=BUCKET, Prefix=prefix, MaxKeys=max_keys)
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        resp = s3.list_objects_v2(**kwargs)
        items = [
            {"key": o["Key"], "size": o.get("Size", 0), "last_modified": o.get("LastModified")}
            for o in resp.get("Contents", [])
        ] if "Contents" in resp else []
        return {
            "bucket": BUCKET,
            "prefix": prefix,
            "is_truncated": resp.get("IsTruncated", False),
            "key_count": resp.get("KeyCount", len(items)),
            "items": items,
            "next_continuation_token": resp.get("NextContinuationToken"),
        }
    except ClientError as e:
        msg = e.response.get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=msg)

@router.get("/presign")
def presign(key: str, expires: int = 3600):
    url = generate_presigned_url(BUCKET, key, expiration=expires, method="get_object")
    if not url:
        raise HTTPException(status_code=400, detail="Failed to generate presigned URL")
    return {"url": url, "expires_in": expires}

@router.post("/upload")
def upload(key: str = Query(..., description="Destination S3 key"), file: UploadFile = File(...)):
    s3 = get_s3_client()
    extra = {"ServerSideEncryption": "aws:kms"}
    if KMS_KEY:
        extra["SSEKMSKeyId"] = KMS_KEY
    try:
        s3.upload_fileobj(file.file, BUCKET, key, ExtraArgs=extra)
        return {"status": "ok", "bucket": BUCKET, "key": key}
    except ClientError as e:
        msg = e.response.get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=msg)

@router.delete("/object")
def delete_object(key: str):
    s3 = get_s3_client()
    try:
        s3.delete_object(Bucket=BUCKET, Key=key)
        return {"status": "deleted", "bucket": BUCKET, "key": key}
    except ClientError as e:
        msg = e.response.get("Error", {}).get("Message", str(e))
        raise HTTPException(status_code=400, detail=msg)
