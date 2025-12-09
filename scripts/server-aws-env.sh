#!/usr/bin/env bash
# Use repo-local AWS config/creds
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AWS_SHARED_CREDENTIALS_FILE="$ROOT/.aws/credentials"
export AWS_CONFIG_FILE="$ROOT/.aws/config"
export AWS_PROFILE="${AWS_PROFILE:-cti-dev}"
export AWS_REGION="${AWS_REGION:-ca-central-1}"
echo "[aws-env] Using $AWS_PROFILE from $AWS_SHARED_CREDENTIALS_FILE"

# Usage:
# source scripts/aws-env.sh
# python scripts/smoke_put_s3.py