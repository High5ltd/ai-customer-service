"""
PDF Loader — Tầng A → B

Đọc file PDF gốc, extract text từng trang, ghi ra staging JSON.
Không làm sạch gì cả — giữ nguyên text thô để trace lỗi dễ.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pypdf import PdfReader


def load_pdf(pdf_path: Path, staging_dir: Path) -> Path:
    """
    Extract toàn bộ text từ PDF, ghi ra staging JSON.

    Args:
        pdf_path:    Đường dẫn file PDF trong data/raw/pdf/
        staging_dir: Thư mục đích, thường là data/staging/text/

    Returns:
        Đường dẫn file staging JSON vừa tạo.
    """
    staging_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(pdf_path))
    pdf_meta = reader.metadata or {}

    pages = []
    for i, page in enumerate(reader.pages):
        raw_text = page.extract_text() or ""
        pages.append(
            {
                "page_number": i + 1,
                "text": raw_text,           # text thô, chưa clean
                "char_count": len(raw_text),
                "is_empty": not raw_text.strip(),
            }
        )

    # Checksum để detect khi nào file gốc thay đổi
    checksum = _sha256(pdf_path)

    staging_data = {
        "source_file": str(pdf_path),
        "source_type": "pdf",
        "parser": "pypdf",
        "extracted_at": datetime.now(UTC).isoformat(),
        "checksum_sha256": checksum,
        "page_count": len(pages),
        "pdf_metadata": {
            "title": pdf_meta.get("/Title", ""),
            "author": pdf_meta.get("/Author", ""),
            "creator": pdf_meta.get("/Creator", ""),
            "creation_date": str(pdf_meta.get("/CreationDate", "")),
        },
        "pages": pages,
    }

    out_path = staging_dir / f"{pdf_path.stem}.json"
    out_path.write_text(json.dumps(staging_data, ensure_ascii=False, indent=2), encoding="utf-8")

    empty_count = sum(1 for p in pages if p["is_empty"])
    print(f"  [loader] {pdf_path.name}: {len(pages)} trang ({empty_count} trang trống) → {out_path}")

    return out_path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
