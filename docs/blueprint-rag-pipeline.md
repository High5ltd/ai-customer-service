# RAG Pipeline Blueprint

> Tài liệu này định nghĩa kiến trúc mục tiêu cho toàn bộ RAG pipeline.  
> Implement từng phần theo thứ tự ưu tiên — **đừng build hết một lúc**.

---

## 0. Triết lý thiết kế

| Nguyên tắc | Lý do |
|---|---|
| Raw data không bao giờ bị xóa hoặc modify | Để re-parse khi đổi parser, trace lỗi, audit |
| Canonical JSONL là nguồn sự thật để index | Tách biệt ingestion logic khỏi indexing logic |
| Mỗi tầng có schema riêng, validate được | Phát hiện lỗi sớm, không để garbage vào vector store |
| Chunk phải enrich metadata, không chỉ plain text | Filter mạnh hơn, recall cao hơn |
| Hybrid search (dense + sparse) mặc định | Dense-only thường kém hơn trong production |

---

## 1. Cấu trúc thư mục mục tiêu

```
ai-customer-service/
├── data/
│   ├── raw/                        # Tầng A: file gốc, không bao giờ sửa
│   │   ├── pdf/
│   │   ├── html/
│   │   ├── docx/
│   │   ├── csv/
│   │   └── api_exports/
│   │
│   ├── staging/                    # Tầng B: extracted, chưa canonical
│   │   ├── text/                   # plain text đã extract
│   │   ├── tables/                 # bảng dạng JSON rows
│   │   ├── images/                 # ảnh/figure kèm caption
│   │   └── ocr/                    # kết quả OCR nếu có
│   │
│   └── canonical/                  # Tầng C: schema chuẩn, sẵn sàng để index
│       ├── documents.jsonl         # 1 dòng = 1 document
│       └── assets.jsonl            # bảng, ảnh, attachment tách riêng
│
├── schemas/
│   ├── document.schema.json        # Schema validate canonical document
│   ├── chunk.schema.json           # Schema validate chunk trước khi index
│   └── eval_record.schema.json
│
├── src/
│   ├── ingestion/                  # Offline: raw → staging → canonical
│   │   ├── loaders/                # Parse từng định dạng file
│   │   ├── extractors/             # Extract text, table, metadata, layout
│   │   └── normalize/              # Clean, canonicalize, deduplicate
│   │
│   ├── indexing/                   # Offline: canonical → vector store
│   │   ├── chunkers/               # Document-aware chunking
│   │   ├── enrichers/              # Thêm summary, keywords, questions
│   │   ├── embedders/              # Embed content
│   │   ├── stores/                 # Vector store, BM25, doc store
│   │   ├── pipelines/              # build_index, upsert_index, reindex
│   │   └── validators/             # Validate schema, chunk quality
│   │
│   ├── retrieval/                  # Online: query → answer
│   │   ├── query_processing/       # Rewrite, classify, filter
│   │   ├── retrievers/             # Dense, sparse, hybrid
│   │   ├── rerank/                 # Cross-encoder, LLM rerank
│   │   └── answering/              # Generator, citation, guardrails
│   │
│   └── api/                        # FastAPI server
│
└── scripts/
    ├── ingest.sh                   # raw → staging → canonical
    ├── index.sh                    # canonical → vector store
    ├── reindex.sh                  # reindex toàn bộ khi đổi policy
    └── eval.sh
```

---

## 2. Ba tầng dữ liệu

### Tầng A — Raw

**Mục tiêu:** Lưu trữ file gốc nguyên vẹn.

```
data/raw/pdf/policy_001.pdf
data/raw/docx/handbook_2024.docx
data/raw/html/faq_page.html
```

**Quy tắc:**
- Không bao giờ modify file trong `raw/`
- Đặt tên file: `{source_type}_{slug}_{version}.{ext}`
- Lưu manifest JSON kèm theo: `checksum`, `source_uri`, `downloaded_at`

---

### Tầng B — Staging (Extracted)

**Mục tiêu:** Tách nội dung thô từ từng định dạng, giữ cấu trúc tự nhiên của file.

```
data/staging/text/policy_001.json
data/staging/tables/policy_001_tables.json
data/staging/images/policy_001_figures.json
```

**Schema staging text:**

```json
{
  "source_file": "data/raw/pdf/policy_001.pdf",
  "extracted_at": "2026-04-12T10:00:00Z",
  "parser": "pypdf@3.x",
  "pages": [
    {
      "page_number": 1,
      "text": "...",
      "headings": ["Refund Policy"],
      "has_table": false,
      "has_image": false
    }
  ]
}
```

**Các field cần extract:**

| Field | Bắt buộc | Mô tả |
|---|---|---|
| `page_number` | PDF | Số trang gốc |
| `headings` | có thể | Các heading detect được |
| `text` | có | Nội dung text thuần |
| `tables` | nếu có | Dạng `[{headers: [], rows: [[]]}]` |
| `images` | nếu có | Path + caption |
| `language` | nên có | Detect tự động |
| `author` | nếu có | Từ metadata file |
| `created_at` | nếu có | Từ metadata file |

---

### Tầng C — Canonical

**Mục tiêu:** Đưa tất cả về 1 schema chung, bất kể nguồn PDF/DOCX/HTML.  
Đây là **nguồn sự thật** — indexing pipeline đọc từ đây, không đọc từ raw.

**`data/canonical/documents.jsonl`** — mỗi dòng là 1 document:

```json
{
  "doc_id": "policy_001",
  "source_type": "pdf",
  "source_uri": "data/raw/pdf/policy_001.pdf",
  "title": "Refund Policy",
  "language": "vi",
  "version": "2026-03-01",
  "sections": [
    {
      "section_id": "policy_001::s1",
      "heading_path": ["Refund Policy", "Eligibility"],
      "content": "Khách hàng có thể yêu cầu hoàn tiền trong vòng 30 ngày...",
      "page_start": 2,
      "page_end": 3,
      "has_table": false
    }
  ],
  "metadata": {
    "department": "support",
    "product": "prankbook",
    "access_level": "internal",
    "updated_at": "2026-03-01T00:00:00Z"
  }
}
```

---

## 3. Schema Chunk (sau khi chunking + enrichment)

Đây là schema của 1 chunk được lưu vào vector store.  
**Quan trọng:** chunk không chỉ chứa `content` — phải enrich đầy đủ.

```json
{
  "chunk_id": "policy_001::chunk_0007",
  "doc_id": "policy_001",
  "parent_section_id": "policy_001::s1",
  "heading_path": ["Refund Policy", "Eligibility"],

  "content": "Khách hàng có thể yêu cầu hoàn tiền trong vòng 30 ngày...",
  "summary": "Điều kiện đủ điều kiện để yêu cầu hoàn tiền",
  "keywords": ["hoàn tiền", "30 ngày", "điều kiện"],
  "hypothetical_questions": [
    "Khi nào tôi có thể yêu cầu hoàn tiền?",
    "Điều kiện để được hoàn tiền là gì?"
  ],

  "token_count": 142,
  "page_start": 2,
  "page_end": 3,

  "metadata": {
    "product": "prankbook",
    "department": "support",
    "access_level": "internal",
    "language": "vi",
    "updated_at": "2026-03-01T00:00:00Z"
  }
}
```

---

## 4. Preprocessing Pipeline (Tầng A → B → C)

### 4.1 Cleaning (trong bước normalize)

```
raw text
  → unicode normalization (NFKC)
  → remove control characters
  → fix hyphenated line breaks
  → normalize whitespace
  → detect & remove repeating headers/footers
  → filter pages quá ngắn (< 20 ký tự)
```

### 4.2 Canonicalization

```
staging text
  → detect language
  → detect section headings
  → map table → structured rows
  → map image → caption text
  → deduplicate near-duplicate sections
  → gắn metadata: doc_id, source_uri, version, access_level
  → validate schema → ghi ra canonical/documents.jsonl
```

### 4.3 Deduplication

- Dùng hash (SHA256) trên `content` để phát hiện exact duplicate
- Dùng MinHash hoặc cosine similarity trên embedding để phát hiện near-duplicate
- Đánh dấu `is_duplicate: true` thay vì xóa (để trace)

---

## 5. Indexing Pipeline (Tầng C → Vector Store)

### 5.1 Chunking — thứ tự ưu tiên

```
1. Document-aware: theo section/heading từ canonical
2. Semantic: theo coherence (khi không có structure rõ)
3. Fallback: recursive character split (hiện tại đang dùng)
```

### 5.2 Enrichment

Mỗi chunk sau khi split cần enrich thêm:

| Field | Cách tạo | Bắt buộc |
|---|---|---|
| `summary` | LLM call (gpt-4o-mini) | Nên có |
| `keywords` | KeyBERT hoặc LLM | Nên có |
| `hypothetical_questions` | LLM (HyDE approach) | Optional |
| `token_count` | tiktoken | Có |
| `heading_path` | Từ canonical structure | Có |
| `metadata` | Kế thừa từ document | Có |

### 5.3 Embedding

```
embed_fields:
  - content                         # bắt buộc
  - title + content (concatenated)  # optional, cải thiện precision
  - summary                         # optional, index riêng
```

### 5.4 Storage — 3 store

| Store | Dùng cho | Công nghệ hiện tại |
|---|---|---|
| Vector store | Dense search | Qdrant |
| Sparse/BM25 store | Lexical match | Qdrant sparse vectors / BM25Retriever |
| Document store | Full document lookup | PostgreSQL |

### 5.5 Build vs Upsert vs Reindex

| Script | Khi nào chạy |
|---|---|
| `build_index.py` | Lần đầu — index toàn bộ từ canonical |
| `upsert_index.py` | Khi có document mới hoặc cập nhật |
| `reindex.py` | Khi đổi chunk policy / embedding model |

---

## 6. Retrieval Pipeline (Online)

```
user query
  → query rewrite (expand, correct typo)
  → query classification (intent, language, filter)
  → dense retrieval (vector search Qdrant)
  → sparse retrieval (BM25)
  → hybrid fusion (RRF hoặc weighted)
  → rerank (cross-encoder hoặc LLM)
  → build context + citations
  → generate answer
  → guardrails check
```

---

## 7. Roadmap implement

### Phase 1 — Offline ingestion (ưu tiên cao nhất)
- [ ] Tạo cấu trúc `data/raw/`, `data/staging/`, `data/canonical/`
- [ ] Viết `document.schema.json` và `chunk.schema.json`
- [ ] Refactor loader → tách thành `loaders/` riêng từng format
- [ ] Viết `extractors/text_extractor.py` — output staging JSON
- [ ] Viết `normalize/cleaners.py` — các hàm clean (hiện có trong `preprocessor.py`)
- [ ] Viết `normalize/canonicalizer.py` — staging → canonical JSONL
- [ ] Viết `normalize/deduper.py` — hash + near-duplicate detection
- [ ] Script `scripts/ingest.sh` — chạy toàn bộ raw → canonical

### Phase 2 — Indexing pipeline
- [ ] Viết `chunkers/section_chunker.py` — chunk theo canonical sections
- [ ] Viết `enrichers/llm_enricher.py` — gọi LLM để tạo summary, keywords
- [ ] Viết `validators/schema_check.py` và `chunk_quality.py`
- [ ] Viết `pipelines/build_index.py` — canonical → Qdrant + Postgres
- [ ] Viết `pipelines/upsert_index.py` — incremental update
- [ ] Script `scripts/index.sh`

### Phase 3 — Retrieval nâng cao
- [ ] Thêm BM25 / sparse retrieval
- [ ] Viết `retrievers/hybrid.py` — RRF fusion
- [ ] Viết `rerank/cross_encoder.py`
- [ ] Query rewrite + classify

### Phase 4 — Evaluation
- [ ] Tạo eval dataset
- [ ] Viết retrieval metrics (Recall@K, MRR, NDCG)
- [ ] Viết generation metrics (faithfulness, relevance)

---

## 8. Trạng thái hiện tại vs mục tiêu

| Component | Hiện tại | Mục tiêu |
|---|---|---|
| Loader | 1 file, 3 format | Tách `loaders/` riêng từng format |
| Preprocessing | `preprocessor.py` inline | Offline, output staging JSON |
| Canonicalization | Không có | `canonicalizer.py` → JSONL |
| Deduplication | Không có | `deduper.py` |
| Chunking | Recursive char split | Section-aware → semantic → fallback |
| Enrichment | Không có | summary + keywords + questions |
| Embedding | content only | content + title + summary |
| Vector store | Qdrant dense only | Qdrant dense + sparse |
| Document store | PostgreSQL | PostgreSQL (giữ nguyên) |
| Indexing trigger | Inline khi upload | Offline script `index.sh` |
| Reindex | Không có | `reindex.py` |

---

> **Ghi chú implementation:** Bắt đầu từ Phase 1.  
> Code hiện tại trong `RAG/ingestion/` sẽ được refactor dần — không xóa ngay,  
> giữ server chạy được trong suốt quá trình migrate.
