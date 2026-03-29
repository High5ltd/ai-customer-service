from backend.config.settings import get_settings
from backend.retrieval.searcher import SearchResult


def rerank(results: list[SearchResult], min_score: float | None = None) -> list[SearchResult]:
    settings = get_settings()
    threshold = min_score if min_score is not None else settings.retrieval_min_score

    # Filter by score threshold
    filtered = [r for r in results if r.score >= threshold]

    # Deduplicate near-identical chunks (same document + chunk_index)
    seen: set[tuple[str, int]] = set()
    deduped: list[SearchResult] = []
    for result in filtered:
        key = (result.document_id, result.chunk_index)
        if key not in seen:
            seen.add(key)
            deduped.append(result)

    # Sort by score descending
    return sorted(deduped, key=lambda r: r.score, reverse=True)
