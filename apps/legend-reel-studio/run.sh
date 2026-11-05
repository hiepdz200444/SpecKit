#!/usr/bin/env bash
# Legends Reel Studio — chạy trên máy (macOS / Linux)
#   ./run.sh                 → http://localhost:8000
#   PORT=8081 ./run.sh       → đổi cổng
#   HOST=0.0.0.0 ./run.sh    → cho máy khác trong LAN truy cập
#   RELOAD=1 ./run.sh        → tự nạp lại khi sửa code
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "✗ Không tìm thấy lệnh '$PY'."
  echo "  macOS : brew install python@3.12"
  echo "  Ubuntu: sudo apt install python3 python3-venv"
  exit 1
fi

if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "✗ Cần Python 3.11 trở lên, máy bạn đang có $("$PY" -V 2>&1)."
  echo "  Cài bản mới rồi chạy lại bằng: PYTHON=python3.12 ./run.sh"
  exit 1
fi

if [ ! -d .venv ]; then
  echo "→ Tạo virtualenv .venv"
  if ! "$PY" -m venv .venv; then
    echo "✗ Không tạo được .venv."
    echo "  Ubuntu/Debian thiếu module venv: sudo apt install python3-venv"
    exit 1
  fi
fi
# shellcheck disable=SC1091
. .venv/bin/activate

if ! python -c "import fastapi, PIL, edge_tts, multipart" >/dev/null 2>&1; then
  echo "→ Cài dependencies (lần đầu mất 1–2 phút)"
  pip install -q --upgrade pip
  if ! pip install -q -r requirements.txt; then
    echo "✗ pip install thất bại — kiểm tra mạng rồi chạy lại."
    exit 1
  fi
fi

# Gói phụ trợ: giúp Facebook không trả HTTP 400 khi đọc page đối thủ.
# Thiếu cũng không chặn khởi động — chỉ mất đường "dán link là xong".
if ! python -c "import curl_cffi, httpx, h2" >/dev/null 2>&1; then
  echo "→ Cài thêm curl_cffi + httpx (để đọc page Facebook từ máy chủ)"
  if ! pip install -q curl_cffi "httpx[http2]"; then
    echo "  ! Không cài được curl_cffi. Studio vẫn chạy; khi đọc page hãy dùng"
    echo "    "Tải trang HTML lên" hoặc nút bookmark trong tab Reels đối thủ."
  fi
fi

mkdir -p data
echo ""
echo "  Legends Reel Studio  →  http://localhost:$PORT"
echo "  Dữ liệu             →  $(pwd)/data"
echo "  Ctrl + C để tắt. Lần sau chỉ cần chạy lại ./run.sh"
echo ""

RELOAD_FLAG=()
if [ "${RELOAD:-0}" = "1" ]; then RELOAD_FLAG=(--reload); fi
exec python -m uvicorn app:app --app-dir backend --host "$HOST" --port "$PORT" "${RELOAD_FLAG[@]}"
