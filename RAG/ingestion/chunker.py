from dataclasses import dataclass

from RAG.ingestion.loader import Page


@dataclass
class Chunk:
    document_id: str
    chunk_index: int
    text: str
    page_number: int


def chunk_pages(
    pages: list[Page],
    document_id: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in pages:
        page_chunks = _split_text(page.text, chunk_size, chunk_overlap)
        for text in page_chunks:
            if text.strip():
                chunks.append(
                    Chunk(
                        document_id=document_id,
                        chunk_index=chunk_index,
                        text=text.strip(),
                        page_number=page.page_number,
                    )
                )
                chunk_index += 1

    return chunks


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    separators = ["\n\n", "\n", ". ", " ", ""]
    return _recursive_split(text, chunk_size, chunk_overlap, separators)


def _recursive_split(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: list[str],
) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    separator = ""
    remaining_separators = []
    for i, sep in enumerate(separators):
        if sep == "" or sep in text:
            separator = sep
            remaining_separators = separators[i + 1 :]
            break

    splits = text.split(separator) if separator else list(text)
    chunks: list[str] = []
    current = ""

    for split in splits:
        piece = (current + separator + split) if current else split
        if len(piece) <= chunk_size:
            current = piece
        else:
            if current:
                chunks.append(current)
                # Start next chunk with overlap
                overlap_start = max(0, len(current) - chunk_overlap)
                current = current[overlap_start:] + (separator if current else "") + split
                if len(current) > chunk_size:
                    # Recurse with finer separators
                    sub = _recursive_split(current, chunk_size, chunk_overlap, remaining_separators)
                    chunks.extend(sub[:-1])
                    current = sub[-1] if sub else ""
            else:
                sub = _recursive_split(split, chunk_size, chunk_overlap, remaining_separators)
                chunks.extend(sub[:-1])
                current = sub[-1] if sub else ""

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]
