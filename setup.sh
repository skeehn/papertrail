#!/usr/bin/env bash
# PaperTrail one-command setup.
#
#   git clone https://github.com/skeehn/papertrail && cd papertrail
#   ./setup.sh
#   npm run dev
#
# No API keys or cloud accounts are needed to boot. Add a chat model key in
# Settings (http://localhost:3000/settings) and the chat works. Pinecone and
# Neo4j are optional and only add semantic search / the knowledge graph.

set -euo pipefail

cyan() { printf '\033[36m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }
red() { printf '\033[31m%s\033[0m\n' "$1"; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

cyan "==> Checking prerequisites"

if ! command -v node >/dev/null 2>&1; then
  red "Node.js is required (18+). Install from https://nodejs.org"; exit 1
fi
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 18 ]; then
  red "Node 18+ required (found $(node -v))."; exit 1
fi

PYTHON_BIN=""
for candidate in python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PYTHON_BIN="$candidate"; break
    fi
  fi
done
if [ -z "$PYTHON_BIN" ]; then
  red "Python 3.11+ is required. Install from https://python.org"; exit 1
fi
green "    node $(node -v) · $($PYTHON_BIN --version)"

cyan "==> Installing frontend dependencies"
npm install --silent
(cd frontend && npm install --silent)

cyan "==> Creating backend virtualenv (backend/.venv)"
if [ ! -d backend/.venv ]; then
  "$PYTHON_BIN" -m venv backend/.venv
fi
# shellcheck disable=SC1091
backend/.venv/bin/python -m pip install --upgrade pip --quiet
cyan "==> Installing backend dependencies"
backend/.venv/bin/python -m pip install -r backend/requirements.txt --quiet

green ""
green "Setup complete."
echo ""
echo "Next:"
echo "  1. npm run dev                       # starts backend + frontend"
echo "  2. open http://localhost:3000/settings"
echo "  3. paste a chat model API key, hit Save — the chat now works."
echo ""
echo "Get a free key at https://openrouter.ai/keys"
echo "Pinecone + Neo4j are optional (semantic search / knowledge graph)."
