"""
Chunker — cắt section thành chunks nhỏ có overlap.

Input : 1 section từ canonical JSONL
Output: list[dict] chunks, mỗi chunk kế thừa metadata của section
"""

import hashlib


def chunk_section(section: dict, doc: dict, chunk_size: int = 512, chunk_overlap: int = 64) -> list[dict]:
    """
    Cắt 1 section thành nhiều chunks.
    Mỗi chunk giữ nguyên heading_path, page, metadata từ section gốc.
    """
    text = section["content"]
    raw_chunks = _split(text, chunk_size, chunk_overlap)

    chunks = []
    for i, content in enumerate(raw_chunks):
        chunk_id = f"{section['section_id']}::c{i}"
        chunks.append({
            "chunk_id": chunk_id,
            "doc_id": doc["doc_id"],
            "section_id": section["section_id"],
            "chunk_index": i,
            "heading_path": section.get("heading_path", []),
            "content": content,
            "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
            "page_start": section.get("page_start"),
            "page_end": section.get("page_end"),
            "token_count": len(content.split()),
            "metadata": {
                **doc.get("metadata", {}),
                "title": doc.get("title", ""),
                "source_uri": doc.get("source_uri", ""),
                "language": doc.get("language", ""),
            },
        })

    return chunks


def _split(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Recursive character split — ưu tiên tách theo đoạn, rồi câu, rồi từ."""
    separators = ["\n\n", "\n", ". ", " ", ""]
    return _recursive_split(text, chunk_size, chunk_overlap, separators)


def _recursive_split(text: str, chunk_size: int, chunk_overlap: int, separators: list[str]) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    separator = ""
    remaining = []
    for i, sep in enumerate(separators):
        if sep == "" or sep in text:
            separator = sep
            remaining = separators[i + 1:]
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
                overlap_start = max(0, len(current) - chunk_overlap)
                current = current[overlap_start:] + (separator if separator else "") + split
                if len(current) > chunk_size:
                    sub = _recursive_split(current, chunk_size, chunk_overlap, remaining)
                    chunks.extend(sub[:-1])
                    current = sub[-1] if sub else ""
            else:
                sub = _recursive_split(split, chunk_size, chunk_overlap, remaining)
                chunks.extend(sub[:-1])
                current = sub[-1] if sub else ""

    if current.strip():
        chunks.append(current)

    return [c for c in chunks if c.strip()]
