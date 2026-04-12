#!/usr/bin/env bash
# =============================================================================
# scripts/index.sh — Offline indexing: canonical JSONL → Qdrant
#
# Yêu cầu:
#   - Qdrant đang chạy (./runserver.sh hoặc docker compose up -d)
#   - .env có OPENAI_API_KEY
#
# Usage:
#   ./scripts/index.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# --- Load .env ---
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
else
  echo "ERROR: .env không tìm thấy. Copy .env.example → .env và điền OPENAI_API_KEY."
  exit 1
fi

# --- Kích hoạt .venv ---
if [ ! -f ".venv/bin/activate" ]; then
  echo "ERROR: .venv chưa tồn tại. Chạy ./scripts/ingest.sh trước để tạo venv."
  exit 1
fi
source .venv/bin/activate

# --- Cài dependencies nếu chưa có ---
if ! python -c "import openai" &>/dev/null; then
  echo "Cài openai ..."
  pip install --quiet openai
fi
if ! python -c "import qdrant_client" &>/dev/null; then
  echo "Cài qdrant-client ..."
  pip install --quiet qdrant-client
fi

# --- Kiểm tra Qdrant đang chạy ---
QDRANT_PORT="${QDRANT_PORT:-6333}"
if ! curl -sf "http://localhost:${QDRANT_PORT}/readyz" &>/dev/null; then
  echo "ERROR: Qdrant chưa chạy tại localhost:${QDRANT_PORT}."
  echo "  Hãy chạy ./runserver.sh (hoặc docker compose up -d) trước."
  exit 1
fi

echo "========================================"
echo "  RAG Indexing Pipeline"
echo "  Project: $PROJECT_ROOT"
echo "========================================"

python src/indexing/run_index.py
