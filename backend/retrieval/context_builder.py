from dataclasses import dataclass

from backend.retrieval.searcher import SearchResult


@dataclass
class Citation:
    index: int
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    score: float
    text: str


@dataclass
class RetrievalContext:
    context_text: str
    citations: list[Citation]


def build_context(results: list[SearchResult]) -> RetrievalContext:
    if not results:
        return RetrievalContext(context_text="", citations=[])

    parts: list[str] = []
    citations: list[Citation] = []

    for i, result in enumerate(results, start=1):
        parts.append(
            f"[{i}] (Source: {result.filename}, Page {result.page_number})\n{result.text}"
        )
        citations.append(
            Citation(
                index=i,
                document_id=result.document_id,
                filename=result.filename,
                page_number=result.page_number,
                chunk_index=result.chunk_index,
                score=result.score,
                text=result.text,
            )
        )

    context_text = "\n\n".join(parts)
    return RetrievalContext(context_text=context_text, citations=citations)
