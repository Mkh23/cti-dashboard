#!/usr/bin/env bash
set -euo pipefail

# --- Paths ----------------------------------------------------------
ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
API_DIR="$ROOT/api"
WEB_DIR="$ROOT/web"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.yml}"

mkdir -p "$ROOT/.logs" "$ROOT/.pids"

echo "[prod] project root: $ROOT"

# --- 0) DB up + ready -----------------------------------------------
if [ -f "$COMPOSE_FILE" ]; then
  echo "[prod] starting Postgres via docker compose"
  docker compose -f "$COMPOSE_FILE" up -d db
else
  echo "[prod] WARNING: no docker-compose.yml found at $COMPOSE_FILE"
fi

echo "[prod] waiting for Postgres to accept connections..."
ATTEMPTS=60
until docker exec "$(docker compose -f "$COMPOSE_FILE" ps -q db)" \
       pg_isready -U postgres -d cti -h 127.0.0.1 >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS-1))
  if [ $ATTEMPTS -le 0 ]; then
    echo "[prod] ERROR: DB not ready after timeout."
    exit 1
  fi
  sleep 1
done
echo "[prod] Postgres ready."

# --- 1) API: venv + deps + migrations ------------------------------
echo "[prod] ensuring API venv + deps"
python3 -m venv "$API_DIR/.venv" >/dev/null 2>&1 || true
source "$API_DIR/.venv/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r "$API_DIR/requirements.txt" >/dev/null

# Load API env before migrations so Alembic hits the correct DB
DATABASE_URL_DEFAULT="postgresql+psycopg2://postgres:postgres@localhost:5432/cti"
if [ -f "$API_DIR/.env" ]; then
  export $(grep -E '^[A-Z_]+=' "$API_DIR/.env" | xargs)
fi
export DATABASE_URL="${DATABASE_URL:-$DATABASE_URL_DEFAULT}"

echo "[prod] running Alembic migrations"
pushd "$API_DIR" >/dev/null
alembic upgrade head
popd >/dev/null
deactivate

# Kill any existing API on 8000
fuser -k 8000/tcp >/dev/null 2>&1 || true

echo "[prod] starting API (uvicorn, 0.0.0.0:8000)"
(
  cd "$API_DIR"
    source .venv/bin/activate
  # load API env
  if [ -f "$API_DIR/.env" ]; then
    export $(grep -E '^[A-Z_]+=' "$API_DIR/.env" | xargs)
  fi
  # You can adjust workers or reload options here if needed
  uvicorn app.main:app --host 0.0.0.0 --port 8000
) >"$ROOT/.logs/api.prod.log" 2>&1 & echo $! > "$ROOT/.pids/api.prod.pid"

# --- 2) Web: deps + build + start ----------------------------------
echo "[prod] installing web deps"
pushd "$WEB_DIR" >/dev/null
pnpm install >/dev/null

# Ensure correct .env.local (API base URLs)
if grep -q '^NEXT_PUBLIC_API_BASE=' .env.local 2>/dev/null; then
  sed -i 's|^NEXT_PUBLIC_API_BASE=.*|NEXT_PUBLIC_API_BASE=http://157.90.181.99:10001|' .env.local
else
  echo 'NEXT_PUBLIC_API_BASE=http://157.90.181.99:10001' >> .env.local
fi

if grep -q '^INTERNAL_API_BASE=' .env.local 2>/dev/null; then
  sed -i 's|^INTERNAL_API_BASE=.*|INTERNAL_API_BASE=http://127.0.0.1:8000|' .env.local
else
  echo 'INTERNAL_API_BASE=http://127.0.0.1:8000' >> .env.local
fi

echo "[prod] building Next.js (pnpm build)"
pnpm build

popd >/dev/null

# Kill any existing web on 3000
fuser -k 3000/tcp >/dev/null 2>&1 || true

echo "[prod] starting web (Next.js prod, 0.0.0.0:3000)"
(
  cd "$WEB_DIR"
  NODE_ENV=production HOST=0.0.0.0 PORT=3000 pnpm start
) >"$ROOT/.logs/web.prod.log" 2>&1 & echo $! > "$ROOT/.pids/web.prod.pid"

# --- 3) Health checks ----------------------------------------------
sleep 2
echo "[prod] listeners:"
ss -ltnp | egrep '(:8000|:3000)\b' || true

echo "[prod] URLs:"
echo "  API docs:   http://127.0.0.1:8000/docs   (http://157.90.181.99:10001/docs)"
echo "  Web UI:     http://127.0.0.1:3000        (http://157.90.181.99:10002)"

echo "[prod] logs:"
echo "  tail -f $ROOT/.logs/api.prod.log"
echo "  tail -f $ROOT/.logs/web.prod.log"

echo "[prod] done."
