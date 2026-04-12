# Document Indexing (Ingestion Pipeline)

Indexing is the process of loading documents into the RAG system: reading file content, splitting it into chunks, generating embeddings, and storing vectors in Qdrant for later retrieval.

---

## Pipeline Overview

```
File upload
    │
    ▼
load_file()          ← read file content, return list of Pages
    │
    ▼
chunk_pages()        ← split each Page into smaller Chunks
    │
    ▼
embed_chunks()       ← call OpenAI Embeddings API, return vectors
    │
    ▼
qdrant.upsert()      ← store vectors + payload in Qdrant collection
    │
    ▼
repo.update_status() ← update Document status in PostgreSQL
```

---

## How to Index Documents

### Via API (primary method)

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@/path/to/document.pdf"
```

The response returns immediately with `status: "processing"`. The pipeline runs synchronously within the request — by the time the response is returned the document is either `ready` or `failed`.

**Supported file types:**

| Format | MIME type | Notes |
|--------|-----------|-------|
| PDF | `application/pdf` | Text extracted per physical page |
| Word | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Entire document treated as 1 page |
| Text / others | `text/plain`, etc. | Entire file treated as 1 page |

File size limit: `MAX_FILE_SIZE_MB` (default **50 MB**).

---

## Pipeline Steps in Detail

### 1. Load file — `RAG/ingestion/loader.py`

`load_file(file_path, mime_type)` returns `list[Page]`.

```python
@dataclass
class Page:
    page_number: int   # 1-based
    text: str          # stripped plain text
```

- **PDF**: uses `pypdf`; each physical page → one `Page`. Empty pages are skipped.
- **DOCX**: uses `python-docx`; all paragraphs joined with `\n\n` → one `Page`.
- **Text / others**: read as UTF-8; entire file → one `Page`.

### 2. Chunk — `RAG/ingestion/chunker.py`

`chunk_pages(pages, document_id, chunk_size, chunk_overlap)` returns `list[Chunk]`.

```python
@dataclass
class Chunk:
    document_id: str
    chunk_index: int   # 0-based, increments across the entire document
    text: str
    page_number: int
```

**Recursive split algorithm:**  
Splits on `\n\n` → `\n` → `. ` → ` ` → individual characters, in order of preference. Overlap preserves context across chunk boundaries.

**Default configuration** (overridable via `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | `512` | Maximum characters per chunk |
| `CHUNK_OVERLAP` | `64` | Characters of overlap between consecutive chunks |

### 3. Embed — `RAG/ingestion/embedder.py`

`embed_chunks(chunks, batch_size=100)` calls the OpenAI Embeddings API in batches.

**Configuration:**

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `OPENAI_EMBEDDING_DIMENSIONS` | `1536` | Vector dimensionality |

`embed_text(text)` is the single-string variant used at query time.

### 4. Upsert into Qdrant — `RAG/ingestion/pipeline.py`

Each chunk becomes one **Point** in Qdrant:

```json
{
  "id": "<doc_id>_<chunk_index>",
  "vector": [...],
  "payload": {
    "document_id": "uuid",
    "chunk_index": 0,
    "text": "chunk content",
    "page_number": 1,
    "filename": "original filename"
  }
}
```

**Collection:** value of `QDRANT_COLLECTION` (default `documents`).

---

## Document Management

### List all documents

```bash
curl http://localhost:8000/api/v1/documents
```

### Get a single document

```bash
curl http://localhost:8000/api/v1/documents/<doc_id>
```

**Document statuses:**

| Status | Meaning |
|--------|---------|
| `processing` | Ingestion in progress |
| `ready` | Indexed and available for search |
| `failed` | Ingestion failed; see `error_message` |

### Delete a document

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/<doc_id>
```

Removes the document vectors from Qdrant, the physical file from `upload_dir`, and the record from PostgreSQL.

---

## Environment Configuration

`.env` file (or environment variables):

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_DIMENSIONS=1536

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=documents

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ragdb
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpassword

# Ingestion
CHUNK_SIZE=512
CHUNK_OVERLAP=64
UPLOAD_DIR=./uploads
MAX_FILE_SIZE_MB=50
```

---

## Starting the Infrastructure

```bash
docker compose up -d
```

Starts PostgreSQL (port 5432), Qdrant (port 6333), and Redis (port 6379).

Run database migrations:

```bash
alembic upgrade head
```

Start the server:

```bash
./runserver.sh
# or
uvicorn backend.main:app --reload
```

---

## Full Data Flow

```
[Client] POST /api/v1/documents/upload
    │
    ├── Validate file size
    ├── Detect MIME type
    ├── Save file → uploads/<filename>
    │
    ├── ingest_document()
    │     ├── Create Document record (status=processing) → PostgreSQL
    │     ├── load_file()      → list[Page]
    │     ├── chunk_pages()    → list[Chunk]
    │     ├── embed_chunks()   → list[EmbeddedChunk]    [OpenAI API]
    │     ├── qdrant.upsert()  → store vectors           [Qdrant]
    │     └── update_status(ready) → PostgreSQL
    │
    └── [Client] receives DocumentResponse
```
