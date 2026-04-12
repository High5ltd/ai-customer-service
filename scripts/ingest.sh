#!/usr/bin/env bash
# =============================================================================
# scripts/ingest.sh — Offline ingestion: raw PDF → staging → canonical JSONL
#
# Usage:
#   ./scripts/ingest.sh                            # xử lý toàn bộ data/raw/pdf/
#   ./scripts/ingest.sh --file data/raw/pdf/foo.pdf  # xử lý 1 file cụ thể
#   ./scripts/ingest.sh --force                    # extract lại từ đầu
# =============================================================================
set -euo pipefail

# --- Đường dẫn ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# --- Tìm Python system ---
if command -v python3 &>/dev/null; then
  SYS_PYTHON=python3
elif command -v python &>/dev/null; then
  SYS_PYTHON=python
else
  echo "ERROR: Không tìm thấy python hoặc python3."
  exit 1
fi

# --- Tạo .venv nếu chưa có ---
if [ ! -f ".venv/bin/activate" ]; then
  echo "Tạo virtual environment tại .venv/ ..."
  $SYS_PYTHON -m venv .venv
fi

# --- Kích hoạt .venv ---
source .venv/bin/activate
PYTHON=python

# --- Cài dependencies nếu chưa có ---
if ! python -c "import pypdf" &>/dev/null; then
  echo "Cài pypdf ..."
  pip install --quiet pypdf
fi

echo "========================================"
echo "  RAG Ingestion Pipeline"
echo "  Project: $PROJECT_ROOT"
echo "========================================"

# --- Chạy Python ingestion ---
$PYTHON src/ingestion/run_ingest.py "$@"
