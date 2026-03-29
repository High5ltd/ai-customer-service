import re

from backend.retrieval.context_builder import Citation


def extract_used_citations(answer: str, citations: list[Citation]) -> list[Citation]:
    """Return only the citations actually referenced in the answer text."""
    pattern = re.compile(r"\[(\d+)\]")
    referenced_indices = {int(m) for m in pattern.findall(answer)}
    return [c for c in citations if c.index in referenced_indices]
