#!/usr/bin/env bash
set -euo pipefail

# --- configurable defaults ---------------------------------------------------
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-3000}"
DB_SERVICE="${DB_SERVICE:-db}"
RUN_DOCKER_DB="${RUN_DOCKER_DB:-false}"

API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../api" && pwd)"
WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../web" && pwd)"
ROOT_DIR="$(cd "${API_DIR}/.." && pwd)"
# -----------------------------------------------------------------------------

echo "[prod] root: ${ROOT_DIR}"
echo "[prod] API  -> http://${API_HOST}:${API_PORT}"
echo "[prod] Web  -> http://${WEB_HOST}:${WEB_PORT}"

if [[ "${RUN_DOCKER_DB}" == "true" ]]; then
  echo "[prod] starting postgres container (${DB_SERVICE})..."
  cd "${ROOT_DIR}"
  docker compose up -d "${DB_SERVICE}"
fi

echo "[prod] preparing API venv..."
cd "${API_DIR}"
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -r requirements.txt >/dev/null

if [[ ! -f ".env" ]]; then
  echo "[prod] ERROR: api/.env is missing. Please create it before running prod.sh."
  exit 1
fi
export $(grep -E '^[A-Z_]+=' .env | xargs)

echo "[prod] running Alembic migrations..."
alembic upgrade head

echo "[prod] installing web deps..."
cd "${WEB_DIR}"
pnpm install --frozen-lockfile

echo "[prod] building Next.js app..."
pnpm build

echo "[prod] starting production processes..."

# API (gunicorn/uvicorn)
(
  cd "${API_DIR}"
  source .venv/bin/activate
  PYTHONPATH="${API_DIR}" \
    uvicorn app.main:app \
      --host "${API_HOST}" \
      --port "${API_PORT}"
) & API_PID=$!

# Web (Next.js)
(
  cd "${WEB_DIR}"
  PORT="${WEB_PORT}" HOSTNAME="${WEB_HOST}" pnpm start
) & WEB_PID=$!

trap 'echo "[prod] stopping services..."; kill ${API_PID} ${WEB_PID} >/dev/null 2>&1 || true' INT TERM

echo "[prod] services running. Press Ctrl+C to stop."
wait ${API_PID} ${WEB_PID}
