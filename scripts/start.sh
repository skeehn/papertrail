#!/usr/bin/env bash
# Launch PaperTrail (backend + frontend) with health checks.
# Usage: ./scripts/start.sh [--restart]
set -euo pipefail
cd "$(dirname "$0")"

BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

if [[ "${1:-}" == "--restart" ]]; then
  lsof -ti:8000 -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
  echo "Killed existing processes."
fi

if [ -z "$(lsof -ti:8000 2>/dev/null)" ]; then
  echo "→ Starting backend (FastAPI, :8000)"
  (cd backend && nohup .venv/bin/python -m uvicorn app.main:app --port 8000 \
    > /tmp/papertrail_backend.log 2>&1 < /dev/null &)
else
  echo "→ Backend already running on :8000"
fi

if [ -z "$(lsof -ti:3000 2>/dev/null)" ]; then
  echo "→ Starting frontend (Next.js, :3000)"
  (cd frontend && nohup npm run dev > /tmp/papertrail_frontend.log 2>&1 < /dev/null &)
else
  echo "→ Frontend already running on :3000"
fi

wait_for() {
  local name="$1" url="$2" tries="${3:-60}"
  for _ in $(seq 1 "$tries"); do
    if curl -s -m 3 -o /dev/null "$url"; then
      echo "✓ $name ready: $url"
      return 0
    fi
    sleep 1
  done
  echo "✗ $name failed to become ready"
  return 1
}

wait_for "backend" "$BACKEND_URL/health"
wait_for "frontend" "$FRONTEND_URL"

echo
echo "  PaperTrail is running:"
echo "    Web UI    → http://localhost:3000"
echo "    API docs  → http://localhost:8000/docs"
echo
echo "  Logs: /tmp/papertrail_backend.log /tmp/papertrail_frontend.log"
echo "  Stop: kill \$(lsof -ti:8000 -ti:3000)  (or ./scripts/start.sh --restart)"
