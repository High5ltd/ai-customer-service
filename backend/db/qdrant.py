from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from backend.config.settings import get_settings

_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
    return _client


async def ensure_collection() -> None:
    settings = get_settings()
    client = get_qdrant_client()
    collections = await client.get_collections()
    names = [c.name for c in collections.collections]
    if settings.qdrant_collection not in names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.openai_embedding_dimensions,
                distance=Distance.COSINE,
            ),
        )


async def close_qdrant_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
