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
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.error(
            "Unexpected error generating presigned URL for %s/%s: %s",
            bucket,
            key,
            exc,
        )
        return None
