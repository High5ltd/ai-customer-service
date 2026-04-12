"""
Store — upsert chunks đã embed vào Qdrant.
"""

import hashlib
import os
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


def get_client() -> QdrantClient:
    host = os.environ.get("QDRANT_HOST", "localhost")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port)


def ensure_collection(client: QdrantClient, collection: str, dimensions: int) -> None:
    """Tạo collection nếu chưa tồn tại."""
    existing = [c.name for c in client.get_collections().collections]
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
        )
        print(f"  [store] Tạo collection '{collection}' (dims={dimensions})")
    else:
        print(f"  [store] Collection '{collection}' đã tồn tại")


def upsert_chunks(client: QdrantClient, collection: str, embedded_chunks: list[dict]) -> int:
    """
    Upsert danh sách embedded chunks vào Qdrant.
    Point ID = UUID v5 từ chunk_id (deterministic → upsert idempotent).
    """
    points = []
    for chunk in embedded_chunks:
        point_id = _chunk_id_to_uuid(chunk["chunk_id"])
        points.append(
            PointStruct(
                id=point_id,
                vector=chunk["vector"],
                payload={
                    "chunk_id":     chunk["chunk_id"],
                    "doc_id":       chunk["doc_id"],
                    "section_id":   chunk["section_id"],
                    "chunk_index":  chunk["chunk_index"],
                    "heading_path": chunk["heading_path"],
                    "content":      chunk["content"],
                    "page_start":   chunk["page_start"],
                    "page_end":     chunk["page_end"],
                    "token_count":  chunk["token_count"],
                    **chunk.get("metadata", {}),
                },
            )
        )

    client.upsert(collection_name=collection, points=points)
    return len(points)


def _chunk_id_to_uuid(chunk_id: str) -> str:
    """Chuyển chunk_id string thành UUID v5 để dùng làm Qdrant point ID."""
    namespace = uuid.UUID("12345678-1234-5678-1234-567812345678")
    return str(uuid.uuid5(namespace, chunk_id))
