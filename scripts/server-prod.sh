#!/usr/bin/env bash
set -euo pipefail

# ==========================================================
# CTI Production launcher
# - DB via docker compose
# - API deps + migrations + restart via systemd (NO direct uvicorn here)
# - Web deps + build + start (pnpm) with visible progress
# ==========================================================

# --- Safety: do NOT run as root ------------------------------------
if [ "${EUID:-$(id -u)}" -eq 0 ]; then
  echo "[prod] ERROR: Do not run this script with sudo/root."
  echo "[prod] Run as: mahmood"
  exit 1
fi

# --- Config ---------------------------------------------------------
ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
API_DIR="$ROOT/api"
WEB_DIR="$ROOT/web"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker-compose.yml}"

# systemd service that runs uvicorn
API_SERVICE="${API_SERVICE:-cti-api.service}"

# What the browser should use to reach the API (your reverse proxy port)
PUBLIC_API_BASE="${PUBLIC_API_BASE:-http://157.90.181.99:10001}"
# What the server-side Next.js should use to reach the API locally
INTERNAL_API_BASE="${INTERNAL_API_BASE:-http://127.0.0.1:8000}"

mkdir -p "$ROOT/.logs" "$ROOT/.pids"

LOG_API_MIG="$ROOT/.logs/api.migrate.log"
LOG_WEB_INSTALL="$ROOT/.logs/web.pnpm-install.log"
LOG_WEB_BUILD="$ROOT/.logs/web.build.log"
LOG_WEB_RUN="$ROOT/.logs/web.prod.log"

echo "[prod] project root: $ROOT"
echo "[prod] api service:  $API_SERVICE"
echo "[prod] public api:   $PUBLIC_API_BASE"
echo "[prod] internal api: $INTERNAL_API_BASE"
echo "[prod] logs dir:     $ROOT/.logs"

# --- helpers --------------------------------------------------------
kill_pidfile() {
  local pidfile="$1"
  local name="$2"
  if [ -f "$pidfile" ]; then
    local pid
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [ -n "${pid:-}" ] && kill -0 "$pid" >/dev/null 2>&1; then
      echo "[prod] stopping $name (pid=$pid)"
      kill "$pid" >/dev/null 2>&1 || true
      sleep 1
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$pidfile"
  fi
}

load_env_file() {
  local envfile="$1"
  if [ -f "$envfile" ]; then
    # shellcheck disable=SC1090
    set -a
    source "$envfile"
    set +a
  fi
}

ensure_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    return 0
  fi
  echo "[prod] pnpm not found. Trying to enable via corepack..."
  if command -v corepack >/dev/null 2>&1; then
    corepack enable
    corepack prepare pnpm@latest --activate
  fi
  if ! command -v pnpm >/dev/null 2>&1; then
    echo "[prod] ERROR: pnpm is not installed and corepack could not enable it."
    echo "[prod] Fix: install Node (with corepack) or install pnpm globally."
    exit 1
  fi
}

# --- 0) DB up + ready ----------------------------------------------
if [ -f "$COMPOSE_FILE" ]; then
  echo "[prod] starting Postgres via docker compose"
  docker compose -f "$COMPOSE_FILE" up -d db
else
  echo "[prod] WARNING: no docker-compose.yml found at $COMPOSE_FILE"
fi

echo "[prod] waiting for Postgres to accept connections..."
ATTEMPTS=60
DB_CID="$(docker compose -f "$COMPOSE_FILE" ps -q db 2>/dev/null || true)"
if [ -z "${DB_CID:-}" ]; then
  echo "[prod] ERROR: Could not find db container id (docker compose ps -q db)."
  exit 1
fi

until docker exec "$DB_CID" pg_isready -U postgres -d cti -h 127.0.0.1 >/dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS-1))
  if [ "$ATTEMPTS" -le 0 ]; then
    echo "[prod] ERROR: DB not ready after timeout."
    exit 1
  fi
  sleep 1
done
echo "[prod] Postgres ready."

# --- 1) API: venv + deps + migrations ------------------------------
echo "[prod] ensuring API venv + deps"
python3 -m venv "$API_DIR/.venv" >/dev/null 2>&1 || true
# shellcheck disable=SC1090
source "$API_DIR/.venv/bin/activate"

echo "[prod] pip install -r api/requirements.txt (logging to $LOG_API_MIG)"
{
  pip install --upgrade pip
  pip install -r "$API_DIR/requirements.txt"
} 2>&1 | tee "$LOG_API_MIG"

# Load API env before migrations so Alembic hits the correct DB
DATABASE_URL_DEFAULT="postgresql+psycopg2://postgres:postgres@localhost:5432/cti"
load_env_file "$API_DIR/.env"
export DATABASE_URL="${DATABASE_URL:-$DATABASE_URL_DEFAULT}"

echo "[prod] running Alembic migrations (logging continues in $LOG_API_MIG)"
{
  cd "$API_DIR"
  alembic upgrade head
} 2>&1 | tee -a "$LOG_API_MIG"

deactivate

# IMPORTANT: Restart API via systemd (never start uvicorn directly)
echo "[prod] restarting API via systemd: $API_SERVICE"
sudo systemctl daemon-reload
sudo systemctl restart "$API_SERVICE"
sudo systemctl --no-pager --full status "$API_SERVICE" || true

# --- 2) Web: deps + build + start ----------------------------------
ensure_pnpm

echo "[prod] installing web deps (logging to $LOG_WEB_INSTALL)"
pushd "$WEB_DIR" >/dev/null
pnpm install --reporter=append-only 2>&1 | tee "$LOG_WEB_INSTALL"

# Ensure correct .env.local (API base URLs)
touch .env.local

if grep -q '^NEXT_PUBLIC_API_BASE=' .env.local 2>/dev/null; then
  sed -i "s|^NEXT_PUBLIC_API_BASE=.*|NEXT_PUBLIC_API_BASE=$PUBLIC_API_BASE|" .env.local
else
  echo "NEXT_PUBLIC_API_BASE=$PUBLIC_API_BASE" >> .env.local
fi

if grep -q '^INTERNAL_API_BASE=' .env.local 2>/dev/null; then
  sed -i "s|^INTERNAL_API_BASE=.*|INTERNAL_API_BASE=$INTERNAL_API_BASE|" .env.local
else
  echo "INTERNAL_API_BASE=$INTERNAL_API_BASE" >> .env.local
fi

echo "[prod] building Next.js (logging to $LOG_WEB_BUILD)"
pnpm build 2>&1 | tee "$LOG_WEB_BUILD"
popd >/dev/null

# Stop existing web (prefer pid file)
kill_pidfile "$ROOT/.pids/web.prod.pid" "web"

echo "[prod] starting web (Next.js prod, 0.0.0.0:3000) (logging to $LOG_WEB_RUN)"
(
  cd "$WEB_DIR"
  NODE_ENV=production HOST=0.0.0.0 PORT=3000 pnpm start
) >"$LOG_WEB_RUN" 2>&1 & echo $! > "$ROOT/.pids/web.prod.pid"

# --- 3) Health checks ----------------------------------------------
sleep 2
echo "[prod] listeners:"
ss -ltnp | egrep '(:8000|:3000)\b' || true

echo "[prod] URLs:"
echo "  API docs (local):   http://127.0.0.1:8000/docs"
echo "  API docs (public):  $PUBLIC_API_BASE/docs"
echo "  Web UI (public):    http://157.90.181.99:10002"

echo "[prod] logs:"
echo "  API (systemd):   sudo journalctl -u $API_SERVICE -f"
echo "  Web run:         tail -f $LOG_WEB_RUN"
echo "  Web install:     tail -f $LOG_WEB_INSTALL"
echo "  Web build:       tail -f $LOG_WEB_BUILD"
echo "  API migrate:     tail -f $LOG_API_MIG"

echo "[prod] done."