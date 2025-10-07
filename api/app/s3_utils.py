"""
S3 utilities for generating presigned URLs and managing asset access.
"""
import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional


def get_s3_client():
    """Get S3 client with proper configuration."""
    # Use profile if specified
    profile = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE")
    region = os.environ.get("AWS_REGION", "ca-central-1")
    
    if profile:
        session = boto3.Session(profile_name=profile, region_name=region)
        return session.client("s3")
    else:
        return boto3.client("s3", region_name=region)


def generate_presigned_url(
    bucket: str,
    key: str,
    expiration: int = 3600,
    method: str = "get_object"
) -> Optional[str]:
    """
    Generate a presigned URL for S3 object access.
    
    Args:
        bucket: S3 bucket name
        key: Object key in the bucket
        expiration: URL expiration time in seconds (default: 1 hour)
        method: S3 method to presign (default: get_object)
    
    Returns:
        Presigned URL string or None if generation fails
    """
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        # Log error in production
        print(f"Error generating presigned URL: {e}")
        return None
    except Exception as e:
        # Handle case where AWS credentials are not configured
        print(f"Error getting S3 client: {e}")
        return None
