"""
Embedder — gọi OpenAI API để tạo vector cho từng chunk.
Dùng sync client + batch để giảm số lượng API calls.
"""

import os
import time

from openai import OpenAI


def embed_chunks(chunks: list[dict], batch_size: int = 100) -> list[dict]:
    """
    Embed danh sách chunks, trả về chunks đã có thêm field 'vector'.
    Xử lý theo batch để tránh rate limit.
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    dimensions = int(os.environ.get("OPENAI_EMBEDDING_DIMENSIONS", "1536"))

    result = []
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i: i + batch_size]
        texts = [c["content"] for c in batch]

        print(f"  [embedder] Batch {i // batch_size + 1}/{-(-total // batch_size)}: {len(texts)} chunks...")

        try:
            response = client.embeddings.create(
                model=model,
                input=texts,
                dimensions=dimensions,
            )
        except Exception as e:
            print(f"  [embedder] LỖI batch {i // batch_size + 1}: {e}")
            raise

        for chunk, embedding_obj in zip(batch, response.data):
            result.append({**chunk, "vector": embedding_obj.embedding})

        # Nghỉ nhỏ giữa các batch để tránh rate limit
        if i + batch_size < total:
            time.sleep(0.3)

    return result
