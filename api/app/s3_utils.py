# api/app/s3_utils.py
import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional

_s3_client = None

def get_s3_client():
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    profile = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE")
    region  = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "ca-central-1"
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
        _s3_client = session.client("s3")
    else:
        _s3_client = boto3.client("s3", region_name=region)
    return _s3_client

def generate_presigned_url(bucket: str, key: str, expiration: int = 3600, method: str = "get_object") -> Optional[str]:
    try:
        s3 = get_s3_client()
        return s3.generate_presigned_url(method, Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiration)
    except ClientError as e:
        print(f"Error generating presigned URL: {e}")
        return None
