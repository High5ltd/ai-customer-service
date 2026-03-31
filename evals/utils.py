def make_chunk_id(document_id: str, chunk_index: int) -> str:
    """Canonical chunk identifier used across all eval modules: '{document_id}__{chunk_index}'."""
    return f"{document_id}__{chunk_index}"
