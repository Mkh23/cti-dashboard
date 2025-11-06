#!/usr/bin/env python3
"""
End-to-end S3 admin test:
1) PUT object with SSE-KMS
2) HEAD + GET verify
3) (Optional) presigned URL fetch
4) DELETE and verify 404
Exits non-zero on any failure.


How to run it (as the same user/env your FastAPI runs under)
# required envs
export AWS_PROFILE=cti-dashboard
export AWS_REGION=ca-central-1
export CTI_BUCKET=cti-dev-406214277746
# optional if you want to assert a specific KMS key id
# export CTI_KMS_KEY_ID=arn:aws:kms:ca-central-1:406214277746:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

python3 tests/test_s3_admin_e2e.py

"""
import os, sys, io, uuid, time
import boto3
from botocore.exceptions import ClientError

# ----- Config from environment -----
BUCKET   = os.environ.get("CTI_BUCKET", "cti-dev-406214277746")
REGION   = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "ca-central-1"
PROFILE  = os.environ.get("CTI_AWS_PROFILE") or os.environ.get("AWS_PROFILE") or "cti-dashboard"
KMS_KEY  = os.environ.get("CTI_KMS_KEY_ID")  # arn:aws:kms:...
TEST_KEY = f"admin/e2e/{uuid.uuid4().hex}/hello.txt"
TEST_BODY = b"hello from e2e test via RolesAnywhere\n"

USE_PRESIGNED = True  # set False if you don’t want to hit S3 via HTTPS

def fail(msg, e=None):
    if e is not None:
        print(f"[ERROR] {msg}: {e}", file=sys.stderr)
    else:
        print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)

def main():
    print(f"[INFO] profile={PROFILE} region={REGION} bucket={BUCKET}")
    print(f"[INFO] kms_key={KMS_KEY or '(None — will still use SSE-KMS if set below)'}")
    print(f"[INFO] test key={TEST_KEY}")

    # Session & clients
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    s3 = session.client("s3")

    # 1) PUT with SSE-KMS
    extra = {"ServerSideEncryption": "aws:kms"}
    if KMS_KEY:
        extra["SSEKMSKeyId"] = KMS_KEY
    try:
        print("[STEP] put-object")
        s3.put_object(Bucket=BUCKET, Key=TEST_KEY, Body=TEST_BODY, **extra)
    except ClientError as e:
        fail("put-object failed", e)

    # 2) HEAD and verify SSE + key id (if provided)
    try:
        print("[STEP] head-object")
        head = s3.head_object(Bucket=BUCKET, Key=TEST_KEY)
        sse = head.get("ServerSideEncryption")
        kms_id = head.get("SSEKMSKeyId")
        print(f"[INFO] SSE={sse} KMSKeyId={kms_id}")
        if sse != "aws:kms":
            fail(f"expected SSE 'aws:kms', got {sse}")
        if KMS_KEY and (not kms_id or KMS_KEY.split("/")[-1] not in kms_id):
            fail(f"head_object KMS key mismatch. expected endswith {KMS_KEY.split('/')[-1]}, got {kms_id}")
    except ClientError as e:
        fail("head-object failed", e)

    # 3) GET and compare contents
    try:
        print("[STEP] get-object")
        obj = s3.get_object(Bucket=BUCKET, Key=TEST_KEY)
        data = obj["Body"].read()
        if data != TEST_BODY:
            fail("downloaded body does not match uploaded body")
    except ClientError as e:
        fail("get-object failed", e)

    # 4) Optional presigned GET test
    if USE_PRESIGNED:
        try:
            print("[STEP] presigned-url GET")
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": BUCKET, "Key": TEST_KEY},
                ExpiresIn=120,
            )
            # lightweight fetch; requests is optional
            try:
                import requests  # type: ignore
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                if r.content != TEST_BODY:
                    fail("presigned GET content mismatch")
            except ImportError:
                # No requests? Just print the URL so you can curl it.
                print(f"[WARN] 'requests' not installed; curl this to verify:\n{url}")
        except ClientError as e:
            fail("generate_presigned_url failed", e)

    # 5) DELETE and confirm 404 on HEAD
    try:
        print("[STEP] delete-object")
        s3.delete_object(Bucket=BUCKET, Key=TEST_KEY)
    except ClientError as e:
        fail("delete-object failed", e)

    # S3 is eventually consistent for LIST but HEAD is strongly consistent for new/deleted keys in most regions
    time.sleep(1)
    try:
        s3.head_object(Bucket=BUCKET, Key=TEST_KEY)
        fail("object still exists after delete (head succeeded)")
    except ClientError as e:
        code = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        errc = e.response.get("Error", {}).get("Code")
        if code in (404, 403) or errc in ("404", "NoSuchKey", "NotFound", "AccessDenied"):
            print("[OK] deletion confirmed")
        else:
            fail(f"unexpected error on head after delete (code={code} err={errc})", e)

    print("[SUCCESS] E2E S3 admin test passed.")

if __name__ == "__main__":
    main()
