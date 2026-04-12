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

# --- Kích hoạt virtual environment nếu có ---
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

# --- Kiểm tra Python ---
if ! command -v python &>/dev/null; then
  echo "ERROR: python không tìm thấy. Hãy kích hoạt virtual environment trước."
  exit 1
fi

echo "========================================"
echo "  RAG Ingestion Pipeline"
echo "  Project: $PROJECT_ROOT"
echo "========================================"

# --- Chạy Python ingestion ---
python src/ingestion/run_ingest.py "$@"
