#!/usr/bin/env python3
"""
src/ingestion/run_ingest.py — Offline ingestion pipeline

Được gọi bởi scripts/ingest.sh, không chạy trực tiếp.

Flow:
    data/raw/pdf/*.pdf
        → [pdf_loader]    → data/staging/text/*.json
        → [canonicalizer] → data/canonical/documents.jsonl
"""

import argparse
import sys
from pathlib import Path

# Đảm bảo import được khi chạy từ project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.loaders.pdf_loader import load_pdf
from src.ingestion.normalize.canonicalizer import canonicalize

RAW_PDF_DIR = PROJECT_ROOT / "data" / "raw" / "pdf"
STAGING_TEXT_DIR = PROJECT_ROOT / "data" / "staging" / "text"
CANONICAL_DIR = PROJECT_ROOT / "data" / "canonical"


def ingest_file(pdf_path: Path, force: bool = False) -> bool:
    """
    Xử lý 1 file PDF qua toàn bộ pipeline: extract → clean → canonicalize.
    Trả về True nếu thành công.
    """
    print(f"\n[ingest] {pdf_path.name}")

    # Bước 1: Extract PDF → staging JSON
    staging_path = STAGING_TEXT_DIR / f"{pdf_path.stem}.json"
    if staging_path.exists() and not force:
        print(f"  [loader] staging đã tồn tại, bỏ qua (dùng --force để extract lại)")
    else:
        try:
            load_pdf(pdf_path, STAGING_TEXT_DIR)
        except Exception as e:
            print(f"  [loader] LỖI: {e}")
            return False

    # Bước 2: Canonicalize staging → canonical JSONL
    try:
        doc = canonicalize(staging_path, CANONICAL_DIR)
        if not doc:
            return False
    except Exception as e:
        print(f"  [canonicalizer] LỖI: {e}")
        return False

    print(f"  [ingest] OK — doc_id={doc['doc_id']}, sections={doc['section_count']}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Offline ingestion: PDF → staging → canonical JSONL"
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Xử lý 1 file PDF cụ thể (mặc định: toàn bộ data/raw/pdf/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Extract lại từ đầu dù staging JSON đã tồn tại",
    )
    args = parser.parse_args()

    # Xác định danh sách file cần xử lý
    if args.file:
        pdf_files = [args.file]
    else:
        pdf_files = sorted(RAW_PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"Không tìm thấy file PDF trong {RAW_PDF_DIR}")
        sys.exit(1)

    print(f"Tìm thấy {len(pdf_files)} file PDF")
    print(f"  Staging  : {STAGING_TEXT_DIR}")
    print(f"  Canonical: {CANONICAL_DIR}")

    # Xóa canonical cũ nếu build lại toàn bộ
    if not args.file and args.force:
        jsonl = CANONICAL_DIR / "documents.jsonl"
        if jsonl.exists():
            jsonl.unlink()
            print(f"\nĐã xóa {jsonl} để build lại từ đầu")

    # Xử lý từng file
    success, failed = 0, 0
    for pdf_path in pdf_files:
        ok = ingest_file(pdf_path, force=args.force)
        if ok:
            success += 1
        else:
            failed += 1

    # Tổng kết
    print(f"\n{'='*50}")
    print(f"Hoàn tất: {success} thành công, {failed} thất bại")

    jsonl = CANONICAL_DIR / "documents.jsonl"
    if jsonl.exists():
        line_count = sum(1 for _ in jsonl.open(encoding="utf-8"))
        print(f"documents.jsonl: {line_count} document(s)")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
