import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_s3_client():
    """Return a boto3 S3 client, honoring optional profile and region overrides."""
    profile = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE")
    region = (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "ca-central-1"
    )
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
        return session.client("s3")
    return boto3.client("s3", region_name=region)


def generate_presigned_url(
    bucket: str,
    key: str,
    expiration: int = 3600,
    method: str = "get_object",
) -> Optional[str]:
    """Generate a presigned URL for an object, returning None on failure."""
    try:
        s3 = get_s3_client()
        return s3.generate_presigned_url(
            method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiration,
        )
    except ClientError as exc:
        logger.warning(
            "Failed to generate presigned URL for %s/%s: %s", bucket, key, exc
        )
        return None


def delete_object(bucket: str, key: str) -> bool:
    """Delete an object from S3, returning True on success."""
    try:
        s3 = get_s3_client()
        s3.delete_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        logger.warning("Failed to delete S3 object %s/%s: %s", bucket, key, exc)
        return False
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.error("Unexpected error deleting S3 object %s/%s: %s", bucket, key, exc)
        return False


def delete_prefix_objects(bucket: str, prefix: str) -> Optional[int]:
    """
    Delete all objects under a prefix. Returns count deleted, or None on failure.
    Best-effort cleanup; intended for purging a capture folder (image/mask/meta).
    """
    try:
        s3 = get_s3_client()
        deleted = 0
        normalized_prefix = prefix if prefix.endswith("/") else f"{prefix}/"
        continuation = None
        while True:
            params = {"Bucket": bucket, "Prefix": normalized_prefix}
            if continuation:
                params["ContinuationToken"] = continuation
            resp = s3.list_objects_v2(**params)
            contents = resp.get("Contents", [])
            if not contents:
                break
            # Batch delete up to 1000 keys per call
            objects = [{"Key": obj["Key"]} for obj in contents]
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})
            deleted += len(objects)
            if not resp.get("IsTruncated"):
                break
            continuation = resp.get("NextContinuationToken")
        return deleted
    except ClientError as exc:
        logger.warning("Failed to delete S3 prefix %s/%s: %s", bucket, prefix, exc)
        return None
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.error("Unexpected error deleting S3 prefix %s/%s: %s", bucket, prefix, exc)
        return None
