import asyncio
from dataclasses import dataclass

import structlog
from openai import AsyncOpenAI

from backend.config.settings import get_settings
from backend.ingestion.chunker import Chunk

log = structlog.get_logger()

_openai_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        settings = get_settings()
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    vector: list[float]


async def embed_chunks(chunks: list[Chunk], batch_size: int = 100) -> list[EmbeddedChunk]:
    settings = get_settings()
    client = get_openai_client()
    results: list[EmbeddedChunk] = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.text for c in batch]
        log.info("Embedding batch", batch_num=i // batch_size + 1, size=len(batch))

        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
            dimensions=settings.openai_embedding_dimensions,
        )

        for chunk, embedding_data in zip(batch, response.data):
            results.append(EmbeddedChunk(chunk=chunk, vector=embedding_data.embedding))

    return results


async def embed_text(text: str) -> list[float]:
    settings = get_settings()
    client = get_openai_client()
    response = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=[text],
        dimensions=settings.openai_embedding_dimensions,
    )
    return response.data[0].embedding
