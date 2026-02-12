#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="${ROOT_DIR}/api"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-cti}"
DB_USER="${DB_USER:-postgres}"
DB_PASS="${DB_PASS:-postgres}"
DATABASE_URL_DEFAULT="postgresql+psycopg2://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"

echo "[migrate] project root: ${ROOT_DIR}"

if [ ! -d "${API_DIR}/.venv" ]; then
  python3 -m venv "${API_DIR}/.venv"
fi

# shellcheck disable=SC1091
source "${API_DIR}/.venv/bin/activate"
pip install -r "${API_DIR}/requirements.txt" >/dev/null

# Load .env if present
if [ -f "${API_DIR}/.env" ]; then
  export $(grep -E '^[A-Z_]+=' "${API_DIR}/.env" | xargs)
fi

export DATABASE_URL="${DATABASE_URL:-$DATABASE_URL_DEFAULT}"

echo "[migrate] running alembic migrations against: ${DATABASE_URL}"
pushd "${API_DIR}" >/dev/null
alembic upgrade head
popd >/dev/null
