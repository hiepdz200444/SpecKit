#!/usr/bin/env bash
# Legends Reel Studio — local dev server
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
if [ ! -d .venv ]; then
  echo "→ Tạo virtualenv .venv"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate

if ! python -c "import fastapi, PIL, edge_tts" >/dev/null 2>&1; then
  echo "→ Cài dependencies"
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
fi

mkdir -p data
echo "→ Legends Reel Studio: http://0.0.0.0:${PORT:-8000}"
exec uvicorn app:app --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}"
