#!/usr/bin/env bash
set -euo pipefail

# --- config you might tweak ---
API_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../api" && pwd)"
WEB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../web" && pwd)"
DB_SERVICE="db"
DB_NAME="cti"
DB_USER="postgres"
DB_PASS="postgres"
DB_HOST="${DB_HOST:-localhost}"      # use "db" if you prefer container hostname everywhere
DB_PORT="${DB_PORT:-5432}"
DATABASE_URL_DEFAULT="postgresql+psycopg2://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
# -------------------------------

ROOT_DIR="$(cd "${API_DIR}/.." && pwd)"

echo "[dev] project root: ${ROOT_DIR}"

# 0) Ensure DB container is up
echo "[dev] starting database container..."
cd "${ROOT_DIR}"
docker compose up -d "${DB_SERVICE}"

# 1) Wait for DB to accept connections
echo "[dev] waiting for Postgres at ${DB_HOST}:${DB_PORT} ..."
retries=40
until docker compose exec -T "${DB_SERVICE}" bash -lc "pg_isready -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER}" >/dev/null 2>&1; do
  ((retries--)) || { echo "[dev][error] Postgres did not become ready in time."; exit 1; }
  sleep 1
done
echo "[dev] Postgres is ready."

# 2) Ensure target database + postgis exist (idempotent)
echo "[dev] ensuring database '${DB_NAME}' exists..."
docker compose exec -T "${DB_SERVICE}" psql -U "${DB_USER}" -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" | grep -q 1 || \
  docker compose exec -T "${DB_SERVICE}" psql -U "${DB_USER}" -c "CREATE DATABASE ${DB_NAME};"

echo "[dev] enabling postgis extension..."
docker compose exec -T "${DB_SERVICE}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 3) API venv + env + migrations
echo "[dev] preparing API environment..."
cd "${API_DIR}"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# install deps if missing wheels (no-op if already installed)
pip show fastapi >/dev/null 2>&1 || pip install -r requirements.txt

# Ensure .env has DATABASE_URL (if missing, inject default)
if ! grep -q '^DATABASE_URL=' .env 2>/dev/null; then
  echo "DATABASE_URL=${DATABASE_URL_DEFAULT}" >> .env
fi

# export .env to current shell for Alembic
export $(grep -E '^[A-Z_]+=' .env | xargs)

# Fallback if .env didn't define it
export DATABASE_URL="${DATABASE_URL:-$DATABASE_URL_DEFAULT}"

echo "[dev] running alembic migrations against: ${DATABASE_URL}"
alembic upgrade head

# 4) Start API & Web (parallel)
echo "[dev] starting API (Uvicorn) and Web (Next.js) ..."
# API
( cd "${API_DIR}" && \
  PYTHONPATH="${API_DIR}" \
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 \
) & API_PID=$!

# Web
( cd "${WEB_DIR}" && \
  [ -f .env.local ] || echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local && \
  pnpm install && pnpm dev \
) & WEB_PID=$!

trap 'echo "[dev] stopping..."; kill ${API_PID} ${WEB_PID} 2>/dev/null || true' INT TERM

echo "[dev] API:  http://localhost:8000/docs"
echo "[dev] Web:  http://localhost:3000"
echo "[dev] Press Ctrl+C to stop both."

wait ${API_PID} ${WEB_PID}
