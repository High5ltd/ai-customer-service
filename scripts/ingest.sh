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

# --- Tìm Python system (ưu tiên 3.13, tránh 3.14 chưa tương thích asyncpg) ---
if command -v python3.13 &>/dev/null; then
  SYS_PYTHON=python3.13
elif command -v python3.12 &>/dev/null; then
  SYS_PYTHON=python3.12
elif command -v python3.11 &>/dev/null; then
  SYS_PYTHON=python3.11
elif command -v python3 &>/dev/null; then
  SYS_PYTHON=python3
else
  echo "ERROR: Không tìm thấy Python 3.11–3.13."
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

# --- Hướng dẫn inspect output ---
echo ""
echo "Để đọc canonical output:"
echo "  1 document:  jq '.' data/canonical/documents.jsonl | head -80"
echo "  Tất cả:      jq -s '.' data/canonical/documents.jsonl | less"
echo "  Chỉ titles:  jq -r '.title' data/canonical/documents.jsonl"
echo "  Sections:    jq '.sections[] | {id: .section_id, heading: .heading_path[0], chars: .char_count}' data/canonical/documents.jsonl"
