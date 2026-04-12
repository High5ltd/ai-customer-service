#!/usr/bin/env python3
"""
src/indexing/run_index.py — Offline indexing pipeline

Được gọi bởi scripts/index.sh, không chạy trực tiếp.

Flow:
    data/canonical/documents.jsonl
        → [chunker]  section → chunks (~512 chars, overlap 64)
        → [embedder] OpenAI text-embedding-3-small
        → [store]    upsert vào Qdrant
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.indexing.chunker import chunk_section
from src.indexing.embedder import embed_chunks
from src.indexing.store import ensure_collection, get_client, upsert_chunks

CANONICAL_JSONL = PROJECT_ROOT / "data" / "canonical" / "documents.jsonl"

CHUNK_SIZE    = int(os.environ.get("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "64"))
COLLECTION    = os.environ.get("QDRANT_COLLECTION", "documents")
DIMENSIONS    = int(os.environ.get("OPENAI_EMBEDDING_DIMENSIONS", "1536"))


def index_document(doc: dict, client) -> int:
    """Chunk + embed + upsert 1 document. Trả về số chunk đã upsert."""
    doc_id = doc["doc_id"]
    sections = doc.get("sections", [])

    if not sections:
        print(f"  [index] SKIP {doc_id}: không có section nào")
        return 0

    # Chunk tất cả sections
    all_chunks = []
    for section in sections:
        chunks = chunk_section(section, doc, CHUNK_SIZE, CHUNK_OVERLAP)
        all_chunks.extend(chunks)

    print(f"  [index] {doc_id}: {len(sections)} sections → {len(all_chunks)} chunks")

    # Embed
    embedded = embed_chunks(all_chunks)

    # Upsert vào Qdrant
    count = upsert_chunks(client, COLLECTION, embedded)
    print(f"  [index] {doc_id}: upserted {count} vectors vào Qdrant")

    return count


def main():
    if not CANONICAL_JSONL.exists():
        print(f"ERROR: {CANONICAL_JSONL} không tồn tại. Chạy ./scripts/ingest.sh trước.")
        sys.exit(1)

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY chưa được set.")
        sys.exit(1)

    # Đọc tất cả documents từ JSONL
    docs = []
    with CANONICAL_JSONL.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))

    if not docs:
        print("Không có document nào trong documents.jsonl")
        sys.exit(1)

    print(f"Tìm thấy {len(docs)} document(s) trong canonical JSONL")
    print(f"  Chunk size : {CHUNK_SIZE} chars, overlap {CHUNK_OVERLAP} chars")
    print(f"  Collection : {COLLECTION}")
    print(f"  Dimensions : {DIMENSIONS}")

    # Kết nối Qdrant và đảm bảo collection tồn tại
    client = get_client()
    ensure_collection(client, COLLECTION, DIMENSIONS)

    # Index từng document
    total_chunks = 0
    success, failed = 0, 0

    for doc in docs:
        print(f"\n[index] {doc['doc_id']}")
        try:
            count = index_document(doc, client)
            total_chunks += count
            success += 1
        except Exception as e:
            print(f"  [index] LỖI: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Hoàn tất: {success} thành công, {failed} thất bại")
    print(f"Tổng vectors đã index: {total_chunks}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
