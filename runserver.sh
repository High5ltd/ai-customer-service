#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"
# Prefer Poetry from the project venv (see README — avoid system-wide pip installs)
if [ -x "$REPO_ROOT/.venv/bin/poetry" ]; then
    export PATH="$REPO_ROOT/.venv/bin:$PATH"
fi

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[runserver]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[runserver]${NC} $*"; }
log_error() { echo -e "${RED}[runserver]${NC} $*"; }

# ─── Load .env ────────────────────────────────────────────────────────────────
if [ -f .env ]; then
    set -o allexport
    # shellcheck disable=SC1091
    source .env
    set +o allexport
    log_info "Loaded .env"
else
    log_warn ".env not found — copy .env.example to .env and fill in your keys"
    log_warn "Using defaults from .env.example"
    if [ -f .env.example ]; then
        set -o allexport
        # shellcheck disable=SC1091
        source .env.example
        set +o allexport
    fi
fi

APP_PORT="${APP_PORT:-8000}"
POSTGRES_USER="${POSTGRES_USER:-raguser}"
POSTGRES_DB="${POSTGRES_DB:-ragdb}"

# ─── Check prerequisites ──────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    log_error "docker is not installed or not in PATH"
    exit 1
fi
if ! command -v poetry &>/dev/null; then
    log_error "Poetry not found. Use a project venv (not a global install), for example:"
    log_error "  python3.11 -m venv .venv && source .venv/bin/activate && pip install poetry"
    log_error "  poetry config virtualenvs.in-project true && poetry install"
    exit 1
fi
if ! command -v pnpm &>/dev/null; then
    if command -v corepack &>/dev/null; then
        log_info "pnpm not on PATH — enabling via Corepack..."
        corepack enable && corepack prepare pnpm@latest --activate
    else
        log_error "pnpm not found. With Node.js 20+: corepack enable && corepack prepare pnpm@latest --activate"
        exit 1
    fi
fi

# ─── Create uploads dir ───────────────────────────────────────────────────────
mkdir -p "${UPLOAD_DIR:-./uploads}"

# ─── Start databases ──────────────────────────────────────────────────────────
log_info "Starting databases via docker compose..."
docker compose up -d

# ─── Wait for PostgreSQL ──────────────────────────────────────────────────────
log_info "Waiting for PostgreSQL to be ready..."
MAX_TRIES=30
TRIES=0
until docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" &>/dev/null; do
    TRIES=$((TRIES + 1))
    if [ $TRIES -ge $MAX_TRIES ]; then
        log_error "PostgreSQL did not become ready in time"
        docker compose logs postgres
        exit 1
    fi
    sleep 1
done
log_info "PostgreSQL is ready"

# ─── Wait for Qdrant ──────────────────────────────────────────────────────────
log_info "Waiting for Qdrant to be ready..."
TRIES=0
until curl -sf http://localhost:"${QDRANT_PORT:-6333}"/readyz &>/dev/null; do
    TRIES=$((TRIES + 1))
    if [ $TRIES -ge $MAX_TRIES ]; then
        log_warn "Qdrant readiness check timed out — continuing anyway"
        break
    fi
    sleep 1
done
log_info "Qdrant is ready"

# ─── Wait for Redis ───────────────────────────────────────────────────────────
log_info "Waiting for Redis to be ready..."
TRIES=0
until docker compose exec -T redis redis-cli ping &>/dev/null; do
    TRIES=$((TRIES + 1))
    if [ $TRIES -ge $MAX_TRIES ]; then
        log_warn "Redis readiness check timed out — continuing anyway"
        break
    fi
    sleep 1
done
log_info "Redis is ready"

# ─── Install backend dependencies ─────────────────────────────────────────────
log_info "Installing backend dependencies..."
poetry install --no-interaction --quiet

# ─── Run Alembic migrations ───────────────────────────────────────────────────
log_info "Running database migrations..."
poetry run alembic -c alembic/alembic.ini upgrade head
log_info "Migrations complete"

# ─── Install frontend dependencies ────────────────────────────────────────────
if [ ! -d frontend/node_modules ]; then
    log_info "Installing frontend dependencies..."
    (cd frontend && pnpm install --frozen-lockfile)
fi

# ─── Start backend ────────────────────────────────────────────────────────────
log_info "Starting FastAPI backend on port $APP_PORT..."
poetry run uvicorn backend.main:app \
    --host "${APP_HOST:-0.0.0.0}" \
    --port "$APP_PORT" \
    --reload \
    --log-level "${LOG_LEVEL:-info}" &
BACKEND_PID=$!

# ─── Start frontend ───────────────────────────────────────────────────────────
log_info "Starting React frontend on port 5173..."
(cd frontend && pnpm dev) &
FRONTEND_PID=$!

# ─── Print URLs ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  RAG Service is running!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${YELLOW}Frontend:${NC}  http://localhost:5173"
echo -e "  ${YELLOW}Backend:${NC}   http://localhost:$APP_PORT"
echo -e "  ${YELLOW}API Docs:${NC}  http://localhost:$APP_PORT/docs"
echo -e "  ${YELLOW}Health:${NC}    http://localhost:$APP_PORT/health/ready"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Press ${RED}Ctrl+C${NC} to stop all services"
echo ""

# ─── Cleanup on exit ──────────────────────────────────────────────────────────
cleanup() {
    echo ""
    log_info "Shutting down..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    log_info "Stopping databases..."
    docker compose stop
    log_info "Done. Databases stopped. Run 'docker compose down' to remove containers."
}
trap cleanup SIGINT SIGTERM EXIT

# ─── Wait ─────────────────────────────────────────────────────────────────────
wait "$BACKEND_PID" "$FRONTEND_PID"
