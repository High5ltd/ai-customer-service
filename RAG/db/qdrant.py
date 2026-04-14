import httpx
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from RAG.config.settings import get_settings
from RAG.exceptions import InfraUnavailableError

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


def _raise_if_qdrant_transport_error(exc: BaseException) -> None:
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.RemoteProtocolError,
        ),
    ):
        raise InfraUnavailableError("Vector store (Qdrant) is unavailable.") from exc


async def qdrant_await(awaitable):
    """Run a Qdrant async call; map transport errors to InfraUnavailableError (HTTP 503)."""
    try:
        return await awaitable
    except Exception as e:
        _raise_if_qdrant_transport_error(e)
        raise


async def ensure_collection() -> None:
    settings = get_settings()
    client = get_qdrant_client()
    try:
        collections = await client.get_collections()
    except Exception as e:
        _raise_if_qdrant_transport_error(e)
        raise
    names = [c.name for c in collections.collections]
    if settings.qdrant_collection not in names:
        try:
            await client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.openai_embedding_dimensions,
                    distance=Distance.COSINE,
                ),
            )
        except Exception as e:
            _raise_if_qdrant_transport_error(e)
            raise


async def close_qdrant_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
