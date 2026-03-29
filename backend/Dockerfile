# ── Stage 1: build dependencies ───────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.8.3

COPY pyproject.toml ./
RUN poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root --no-interaction

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

COPY --from=builder /app/.venv /app/.venv
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic/alembic.ini ./alembic.ini

RUN mkdir -p /app/uploads && chown appuser:appuser /app/uploads

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
