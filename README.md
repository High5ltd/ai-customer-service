# RAG Service

Retrieval-Augmented Generation service — upload documents, ask questions, get answers with cited sources.

**Stack:** Python 3.11 · FastAPI · OpenAI GPT-4o · Qdrant · PostgreSQL · Redis · React 18 · Vite · Tailwind CSS

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│  ┌─────────────────┐        ┌──────────────────────────┐   │
│  │  Document Panel │        │      Chat Panel          │   │
│  │  ─────────────  │        │  ─────────────────────   │   │
│  │  [+ Upload]     │        │  User: What is X?        │   │
│  │                 │        │                          │   │
│  │  > doc1.pdf ✕  │        │  AI: X is... [1][2]      │   │
│  │    doc2.txt ✕  │        │  ▼ Sources (2)           │   │
│  │                 │        │  ──────────────────────  │   │
│  │                 │        │  [Ask something...]  ↑   │   │
│  └─────────────────┘        └──────────────────────────┘   │
└────────────────────────────────┬────────────────────────────┘
                                 │ HTTP + SSE
                    ┌────────────▼────────────┐
                    │     FastAPI Backend      │
                    │  ┌────────────────────┐ │
                    │  │  ingestion/        │ │   Upload flow
                    │  │  loader → chunker  │ │ ──────────────
                    │  │  → embedder        │ │   file → text
                    │  └────────────────────┘ │   → chunks
                    │  ┌────────────────────┐ │   → vectors
                    │  │  pipeline/         │ │
                    │  │  retrieval         │ │   Query flow
                    │  │  → generation      │ │ ──────────────
                    │  │  → SSE stream      │ │   question
                    │  └────────────────────┘ │   → embed
                    └──┬──────────┬───────┬───┘   → search
                       │          │       │        → generate
                  ┌────▼─┐  ┌────▼─┐ ┌──▼───┐    → stream
                  │Qdrant│  │  PG  │ │Redis │
                  │vectors│ │ meta │ │cache │
                  └──────┘  └──────┘ └──────┘
```

---

## Project Structure

```
RAG/
├── .env.example                  # Environment variables template
├── pyproject.toml                # Python dependencies (Poetry)
├── docker-compose.yml            # Databases ONLY (Qdrant, PostgreSQL, Redis)
├── runserver.sh                  # One-command startup script
│
├── backend/
│   ├── main.py                   # FastAPI app + lifespan
│   ├── config/
│   │   └── settings.py           # Pydantic BaseSettings (reads .env)
│   ├── api/
│   │   ├── router.py
│   │   ├── dependencies.py
│   │   ├── routes/
│   │   │   ├── documents.py      # Upload / list / delete documents
│   │   │   ├── chat.py           # Chat (POST) + streaming (SSE GET)
│   │   │   └── health.py         # /health · /health/ready
│   │   └── schemas/              # Pydantic request/response models
│   ├── ingestion/
│   │   ├── loader.py             # Extract text from PDF / DOCX / TXT
│   │   ├── chunker.py            # Recursive character splitter
│   │   ├── embedder.py           # Batched OpenAI embeddings
│   │   └── pipeline.py           # Orchestrate load → chunk → embed → store
│   ├── retrieval/
│   │   ├── searcher.py           # Qdrant ANN search
│   │   ├── reranker.py           # Score threshold + deduplication
│   │   └── context_builder.py    # Format context [1]…[N] + citations
│   ├── generation/
│   │   ├── prompts.py            # System + user prompt templates
│   │   ├── llm_client.py         # AsyncOpenAI wrapper (stream / non-stream)
│   │   └── response_parser.py    # Extract [N] citation references
│   ├── pipeline/
│   │   ├── rag_pipeline.py       # query() + stream_query() orchestration
│   │   └── session_manager.py    # Conversation history in Redis
│   └── db/
│       ├── postgres.py           # SQLAlchemy async engine
│       ├── qdrant.py             # AsyncQdrantClient singleton
│       ├── redis.py              # aioredis singleton
│       ├── models/document.py    # ORM model
│       └── repositories/         # CRUD layer
│
├── frontend/
│   └── src/
│       ├── api/                  # axios client + SSE chat handler
│       ├── components/
│       │   ├── chat/             # ChatWindow · MessageList · ChatInput · SourcesPanel
│       │   ├── documents/        # DocumentSidebar · DocumentList · DocumentUpload
│       │   └── shared/           # LoadingSpinner · ErrorBanner · EmptyState
│       ├── hooks/                # useChat · useDocuments
│       ├── store/                # Zustand stores (chat · documents)
│       └── types/                # TypeScript interfaces
│
├── alembic/                      # Database migrations
├── tests/
│   ├── unit/                     # test_chunker · test_prompts
│   └── integration/              # test_api_documents
│
└── deploy/
    ├── app/                      # Dockerfiles + docker-compose.app.yml (staging/prod)
    │   ├── backend/Dockerfile    # Multi-stage Python image
    │   └── frontend/Dockerfile   # Node build → Nginx
    └── infra/                    # Production-tuned infra
        ├── docker-compose.infra.yml
        └── k8s/                  # Kubernetes manifests (stubs)
```

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Docker + Docker Compose | v2+ |
| Python | 3.11+ |
| Poetry | 1.8+ |
| Node.js | 20+ |
| pnpm | 9+ |

**Python / Poetry (project venv — do not install into the system Python):**
```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip poetry
poetry config virtualenvs.in-project true
poetry install
```
After the first setup, activate `.venv` in each terminal before running `poetry` commands.

**pnpm (via Corepack — no global npm install):**
```bash
corepack enable
corepack prepare pnpm@latest --activate
```
Requires Node.js 20+.

### 1. Configure environment

```bash
cp .env.example .env
```

Open `.env` and set at minimum:
```env
OPENAI_API_KEY=sk-...
```

All other values have sensible defaults for local development.

### 2. Start everything

```bash
./runserver.sh
```

The script will:
1. Start Qdrant, PostgreSQL, Redis via Docker Compose
2. Wait for all databases to be healthy
3. Install Python dependencies (`poetry install`)
4. Run database migrations (`alembic upgrade head`)
5. Install frontend dependencies (`pnpm install`) if needed
6. Start FastAPI backend on `:8000`
7. Start Vite dev server on `:5173`

**Press `Ctrl+C` to stop** — all services including databases are gracefully shut down.

### 3. Open the app

| Service | URL |
|---------|-----|
| UI | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health/ready |

---

## Usage

### Upload a document

Drag and drop or click **+ Upload document** in the left panel. Supported formats:
- PDF (`.pdf`)
- Word (`.docx`, `.doc`)
- Plain text (`.txt`, `.md`)

The document is processed asynchronously:
- `processing` → text extracted, chunked, embedded
- `ready` → available for search
- `failed` → error shown on hover

### Ask a question

Type in the chat input and press **Enter** (or Shift+Enter for a new line). The answer streams in real time. Click **▼ Sources** below any answer to see the retrieved document chunks with relevance scores.

---

## API Reference

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload a document (multipart/form-data) |
| `GET` | `/api/v1/documents` | List all documents |
| `GET` | `/api/v1/documents/{id}` | Get document details |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + vectors |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat` | Non-streaming chat |
| `GET` | `/api/v1/chat/stream` | Streaming chat (SSE) — `?question=...&session_id=...` |
| `DELETE` | `/api/v1/chat/session/{id}` | Clear conversation history |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/health/ready` | Readiness check (PostgreSQL + Qdrant + Redis) |

#### SSE stream format

```
data: "token1"
data: "token2"
...
event: citations
data: [{"index":1,"filename":"doc.pdf","page_number":3,...}]

data: [DONE]
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | OpenAI API key |
| `OPENAI_CHAT_MODEL` | `gpt-4o` | Chat model |
| `OPENAI_FAST_MODEL` | `gpt-4o-mini` | Faster/cheaper model |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `ragdb` | Database name |
| `POSTGRES_USER` | `raguser` | Database user |
| `POSTGRES_PASSWORD` | `ragpassword` | Database password |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `QDRANT_COLLECTION` | `documents` | Collection name |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `APP_PORT` | `8000` | Backend port |
| `UPLOAD_DIR` | `./uploads` | File storage directory |
| `MAX_FILE_SIZE_MB` | `50` | Upload size limit |
| `CHUNK_SIZE` | `512` | Characters per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap between chunks |
| `RETRIEVAL_TOP_K` | `5` | Max chunks to retrieve |
| `RETRIEVAL_MIN_SCORE` | `0.4` | Minimum similarity score (0–1) |

---

## Development

### Run only the databases

```bash
docker compose up -d
```

### Run backend only

```bash
poetry install
poetry run alembic -c alembic/alembic.ini upgrade head
poetry run uvicorn backend.main:app --reload
```

### Run frontend only

```bash
cd frontend
pnpm install
pnpm dev
```

### Run tests

```bash
# Unit tests (no external services needed)
poetry run pytest tests/unit -v

# Integration tests (requires running databases + OPENAI_API_KEY)
poetry run pytest tests/integration -v -m integration
```

### Database migrations

```bash
# Create a new migration
poetry run alembic -c alembic/alembic.ini revision --autogenerate -m "description"

# Apply migrations
poetry run alembic -c alembic/alembic.ini upgrade head

# Rollback one step
poetry run alembic -c alembic/alembic.ini downgrade -1
```

---

## Deployment

### Staging / Production (Docker)

Builds and runs all services including the app as containers:

```bash
cd deploy/app
docker compose -f docker-compose.app.yml --env-file ../../.env up -d
```

This starts: Qdrant + PostgreSQL + Redis + FastAPI backend + Nginx frontend (port 80).

### Kubernetes

Stub manifests are in `deploy/infra/k8s/`. Apply the namespace first, then each service:

```bash
kubectl apply -f deploy/infra/k8s/namespace.yaml
kubectl apply -f deploy/infra/k8s/
```

A `Secret` named `rag-secrets` with the database credentials is expected in the `rag` namespace.

---

## How It Works

### Upload flow

```
POST /api/v1/documents/upload
  → save file to disk
  → loader.py   — extract text pages (PDF/DOCX/TXT)
  → chunker.py  — split into overlapping chunks (512 chars, 64 overlap)
  → embedder.py — batch embed with text-embedding-3-small (OpenAI)
  → Qdrant      — upsert vectors with payload {document_id, text, page_number}
  → PostgreSQL  — update document status to "ready"
```

### Query flow (streaming)

```
GET /api/v1/chat/stream?question=...&session_id=...
  → embed question (OpenAI)
  → Qdrant ANN search (top_k=5)
  → reranker — filter by min_score, deduplicate
  → context_builder — format [1]...[N] numbered context
  → Redis — load conversation history
  → GPT-4o stream — yield tokens via SSE
  → response_parser — extract [N] citation references
  → Redis — save turn to session history
  → SSE event: citations JSON
  → SSE: [DONE]
```

---

## License

MIT
