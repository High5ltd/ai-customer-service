"""
Canonicalizer — Tầng B → C

Đọc staging JSON, chuẩn hóa về canonical schema, ghi ra documents.jsonl.
Canonical = nguồn sự thật để indexing pipeline đọc vào.
"""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from src.ingestion.normalize.cleaners import (
    clean_text,
    detect_headers_footers,
    detect_language,
    is_heading_line,
    remove_headers_footers,
)


def canonicalize(staging_path: Path, canonical_dir: Path) -> dict:
    """
    Chuyển 1 staging JSON → canonical document record.

    Args:
        staging_path:  File JSON trong data/staging/text/
        canonical_dir: Thư mục đích, thường là data/canonical/

    Returns:
        Dict canonical document (cũng được append vào documents.jsonl).
    """
    canonical_dir.mkdir(parents=True, exist_ok=True)

    staging = json.loads(staging_path.read_text(encoding="utf-8"))
    pages_raw = staging["pages"]

    # --- Bước 1: Clean text từng trang ---
    pages_clean = []
    for p in pages_raw:
        if p["is_empty"]:
            continue
        cleaned = clean_text(p["text"])
        if len(cleaned) >= 20:  # lọc trang quá ngắn sau khi clean
            pages_clean.append({"page_number": p["page_number"], "text": cleaned})

    if not pages_clean:
        print(f"  [canonicalizer] SKIP {staging_path.name}: không còn nội dung sau clean")
        return {}

    # --- Bước 2: Detect & remove header/footer ---
    texts = [p["text"] for p in pages_clean]
    headers, footers = detect_headers_footers(texts)
    if headers or footers:
        print(f"  [canonicalizer] Phát hiện header/footer: {headers | footers}")
        for p in pages_clean:
            p["text"] = remove_headers_footers(p["text"], headers, footers)

    # Lọc lại sau khi xóa header/footer
    pages_clean = [p for p in pages_clean if len(p["text"]) >= 20]

    # --- Bước 3: Detect language (dựa trên toàn bộ nội dung) ---
    full_text = "\n\n".join(p["text"] for p in pages_clean)
    language = detect_language(full_text)

    # --- Bước 4: Tách sections theo heading ---
    sections = _build_sections(pages_clean, staging_path.stem)

    # --- Bước 5: Tạo doc_id từ tên file ---
    doc_id = _slugify(staging_path.stem)

    # --- Bước 6: Lấy title ---
    pdf_meta = staging.get("pdf_metadata", {})
    title = (
        pdf_meta.get("title", "").strip()
        or _infer_title(pages_clean)
        or staging_path.stem
    )

    # --- Bước 7: Build canonical record ---
    doc = {
        "doc_id": doc_id,
        "source_type": staging.get("source_type", "pdf"),
        "source_uri": staging["source_file"],
        "checksum_sha256": staging.get("checksum_sha256", ""),
        "title": title,
        "language": language,
        "page_count": staging["page_count"],
        "section_count": len(sections),
        "sections": sections,
        "metadata": {
            "author": pdf_meta.get("author", ""),
            "access_level": "internal",
            "updated_at": datetime.now(UTC).isoformat(),
            "indexed_at": None,  # sẽ được điền khi index
        },
    }

    # --- Bước 8: Append vào documents.jsonl ---
    jsonl_path = canonical_dir / "documents.jsonl"
    _append_jsonl(jsonl_path, doc)

    print(
        f"  [canonicalizer] {staging_path.name}: "
        f"{len(sections)} sections, ngôn ngữ={language} → {jsonl_path}"
    )

    return doc


def _build_sections(pages: list[dict], doc_stem: str) -> list[dict]:
    """
    Chia pages thành sections dựa trên heading detection.

    Nếu không tìm thấy heading nào → mỗi page là 1 section.
    """
    sections = []
    section_index = 0
    current_heading_path: list[str] = []
    current_lines: list[str] = []
    current_page_start: int = pages[0]["page_number"] if pages else 1
    current_page_end: int = current_page_start

    def flush_section(page_end: int):
        nonlocal section_index
        content = "\n".join(current_lines).strip()
        if not content:
            return
        section_id = f"{_slugify(doc_stem)}::s{section_index}"
        sections.append(
            {
                "section_id": section_id,
                "heading_path": list(current_heading_path) or ["(no heading)"],
                "content": content,
                "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                "page_start": current_page_start,
                "page_end": page_end,
                "char_count": len(content),
            }
        )
        section_index += 1

    for page in pages:
        page_lines = page["text"].split("\n")
        for line in page_lines:
            if is_heading_line(line):
                # Lưu section hiện tại trước khi bắt đầu section mới
                if current_lines:
                    flush_section(current_page_end)
                    current_lines = []
                current_page_start = page["page_number"]
                current_heading_path = [line.strip()]
            else:
                current_lines.append(line)
        current_page_end = page["page_number"]

    # Flush section cuối cùng
    if current_lines:
        flush_section(current_page_end)

    # Fallback: nếu không tìm thấy section nào → 1 section per page
    if not sections:
        for page in pages:
            section_id = f"{_slugify(doc_stem)}::s{section_index}"
            content = page["text"].strip()
            sections.append(
                {
                    "section_id": section_id,
                    "heading_path": ["(no heading)"],
                    "content": content,
                    "content_hash": hashlib.sha256(content.encode()).hexdigest()[:16],
                    "page_start": page["page_number"],
                    "page_end": page["page_number"],
                    "char_count": len(content),
                }
            )
            section_index += 1

    return sections


def _infer_title(pages: list[dict]) -> str:
    """Lấy dòng đầu tiên của trang 1 làm title nếu PDF không có metadata title."""
    if not pages:
        return ""
    first_lines = [ln.strip() for ln in pages[0]["text"].split("\n") if ln.strip()]
    if first_lines:
        candidate = first_lines[0]
        if len(candidate) <= 120:
            return candidate
    return ""


def _slugify(text: str) -> str:
    """Chuyển tên file thành doc_id an toàn."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _append_jsonl(path: Path, record: dict) -> None:
    """Append 1 record vào file JSONL (1 dòng = 1 JSON object)."""
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
