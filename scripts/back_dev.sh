#!/usr/bin/env bash
set -e

# 1) DB
cd ~/projects/cti-dashboard
docker compose up -d

# 2) API
cd api
source .venv/bin/activate
# run uvicorn in background
( uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & ) 
API_PID=$!

# 3) Web
cd ../web
pnpm dev

# If you stop pnpm dev, also stop uvicorn
kill $API_PID 2>/dev/null || true
