#!/usr/bin/env bash
set -euo pipefail

echo "[kill] stopping services"
sudo systemctl stop cti-web.service cti-api.service cti-bootstrap.service || true

echo "[kill] freeing ports 3000/8000"
sudo fuser -k 3000/tcp 2>/dev/null || true
sudo fuser -k 8000/tcp 2>/dev/null || true

echo "[kill] killing leftover processes"
pkill -f "next start"   || true
pkill -f "node .*next"  || true
pkill -f "uvicorn"      || true

echo "[kill] showing listeners (should be empty for 3000/8000)"
ss -ltnp | egrep '(:8000|:3000)\b' || true

echo "[kill] done."

ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

echo "[kill] stopping dev web/api if present"
# Kill by PID files
for name in api web; do
  if [ -f "$ROOT/.pids/${name}.pid" ]; then
    PID=$(cat "$ROOT/.pids/${name}.pid" || true)
    if [ -n "${PID:-}" ] && ps -p "$PID" >/dev/null 2>&1; then
      kill "$PID" || true
    fi
    rm -f "$ROOT/.pids/${name}.pid"
  fi
done

# Kill by port (belt & suspenders)
fuser -k 3000/tcp 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
pkill -f "uvicorn app.main:app" || true
pkill -f "pnpm dev" || true
pkill -f "next dev" || true

echo "[kill] (optional) stop db container:"
echo "       docker compose -f \"$ROOT/docker-compose.yml\" stop db"