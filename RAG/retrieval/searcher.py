from dataclasses import dataclass

from qdrant_client.models import FieldCondition, Filter, MatchAny

from RAG.config.settings import get_settings
from RAG.db.qdrant import get_qdrant_client, qdrant_await


@dataclass
class SearchResult:
    score: float
    text: str
    document_id: str
    chunk_index: int
    page_number: int
    filename: str


async def search(
    query_vector: list[float],
    top_k: int | None = None,
    document_ids: list[str] | None = None,
) -> list[SearchResult]:
    settings = get_settings()
    client = get_qdrant_client()
    k = top_k or settings.retrieval_top_k

    query_filter = None
    if document_ids:
        query_filter = Filter(
            must=[FieldCondition(key="document_id", match=MatchAny(any=document_ids))]
        )

    response = await qdrant_await(
        client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            limit=k,
            query_filter=query_filter,
            with_payload=True,
        )
    )

    return [
        SearchResult(
            score=hit.score,
            text=hit.payload.get("text", ""),
            document_id=hit.payload.get("document_id", ""),
            chunk_index=hit.payload.get("chunk_index", 0),
            page_number=hit.payload.get("page_number", 1),
            filename=hit.payload.get("filename", ""),
        )
        for hit in response.points
    ]
