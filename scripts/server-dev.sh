#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
API_DIR="$ROOT/api"
WEB_DIR="$ROOT/web"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.yml}"

# NEW: ensure folders for logs & pids
mkdir -p "$ROOT/.logs" "$ROOT/.pids"

echo "[dev] project root: $ROOT"

# Docker up (db)
docker compose -f "$COMPOSE_FILE" up -d db

# Wait for Postgres
echo "[dev] waiting for Postgres to accept connections..."
ATTEMPTS=60
until docker exec "$(docker compose -f "$COMPOSE_FILE" ps -q db)" pg_isready -U postgres -d cti -h 127.0.0.1 >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS-1)); [ $ATTEMPTS -le 0 ] && { echo "[dev] DB not ready"; exit 1; }
  sleep 1
done
echo "[dev] Postgres ready."

# API venv + deps
python3 -m venv "$API_DIR/.venv" >/dev/null 2>&1 || true
source "$API_DIR/.venv/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r "$API_DIR/requirements.txt"

# Alembic (load env so migrations hit the same DB as the API)
DATABASE_URL_DEFAULT="postgresql+psycopg2://postgres:postgres@localhost:5432/cti"
if [ -f "$API_DIR/.env" ]; then
  export $(grep -E '^[A-Z_]+=' "$API_DIR/.env" | xargs)
fi
export DATABASE_URL="${DATABASE_URL:-$DATABASE_URL_DEFAULT}"

pushd "$API_DIR" >/dev/null
alembic upgrade head
popd >/dev/null

# Start API (0.0.0.0:8000)
fuser -k 8000/tcp >/dev/null 2>&1 || true
( cd "$API_DIR" && . .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 ) \
  >"$ROOT/.logs/api.dev.log" 2>&1 & echo $! > "$ROOT/.pids/api.pid"

# Web deps (dev)
pushd "$WEB_DIR" >/dev/null
pnpm install
# Point UI directly at API in dev:
if grep -q '^NEXT_PUBLIC_API_BASE=' .env.local 2>/dev/null; then
  sed -i 's|^NEXT_PUBLIC_API_BASE=.*|NEXT_PUBLIC_API_BASE=http://157.90.181.99:10001|' .env.local
else
  echo 'NEXT_PUBLIC_API_BASE=http://157.90.181.99:10001' >> .env.local
fi
popd >/dev/null

# Start web (0.0.0.0:3000)
fuser -k 3000/tcp >/dev/null 2>&1 || true
( cd "$WEB_DIR" && PORT=3000 HOST=0.0.0.0 pnpm dev ) \
  >"$ROOT/.logs/web.dev.log" 2>&1 & echo $! > "$ROOT/.pids/web.pid"

# Show listeners
sleep 1
echo "[dev] listeners:"
ss -ltnp | egrep '(:3000|:8000)\b' || true

echo "[dev] URLs:"
echo "  API docs:   http://127.0.0.1:8000/docs   (http://10.10.10.104:8000/docs)"
echo "  Web UI:     http://127.0.0.1:3000        (http://10.10.10.104:3000)"
echo "[dev] logs:"
echo "  tail -f $ROOT/.logs/api.dev.log"
echo "  tail -f $ROOT/.logs/web.dev.log"
