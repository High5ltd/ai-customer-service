import re
import unicodedata
from collections import Counter

import structlog

from RAG.ingestion.loader import Page

log = structlog.get_logger()


def preprocess_pages(
    pages: list[Page],
    min_page_length: int = 20,
    detect_headers_footers: bool = True,
    header_footer_lines: int = 2,
) -> list[Page]:
    """
    Tiền xử lý văn bản sau khi load, trước khi chunking.

    Các bước:
      1. Unicode normalization (NFKC)
      2. Loại bỏ control characters
      3. Fix hyphenated line breaks (busi-\\nness → business)
      4. Normalize whitespace
      5. Phát hiện và xóa header/footer lặp lại qua các trang
      6. Lọc bỏ trang có nội dung quá ngắn
    """
    if not pages:
        return pages

    original_count = len(pages)

    # Bước 1–4: Clean text từng trang
    cleaned = [_clean_page(p) for p in pages]

    # Bước 5: Xóa header/footer lặp lại (chỉ có ý nghĩa với tài liệu nhiều trang)
    if detect_headers_footers and len(cleaned) > 2:
        before = len(cleaned)
        cleaned = _remove_headers_footers(cleaned, header_footer_lines)
        log.debug("Header/footer removal done", pages=before)

    # Bước 6: Lọc trang quá ngắn
    cleaned = [p for p in cleaned if len(p.text) >= min_page_length]

    log.info(
        "Preprocessing complete",
        original_pages=original_count,
        remaining_pages=len(cleaned),
        removed_pages=original_count - len(cleaned),
    )

    return cleaned


def _clean_page(page: Page) -> Page:
    text = page.text

    # 1. Unicode normalization — chuẩn hóa ký tự (ví dụ: ﬁ → fi, ² → 2)
    text = unicodedata.normalize("NFKC", text)

    # 2. Xóa null bytes và control characters
    #    Giữ lại: \n (0x0A), \t (0x09), \r (0x0D) — \r sẽ được chuẩn hóa ở bước sau
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # 3. Xóa soft hyphens (U+00AD) không in được
    text = text.replace("\u00ad", "")

    # 4. Chuẩn hóa line endings: \r\n và \r → \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Fix hyphenated line breaks: "busi-\nness" → "business"
    text = re.sub(r"-\n(\w)", r"\1", text)

    # 6. Collapse nhiều space/tab liên tiếp thành một space (không đụng đến \n)
    text = re.sub(r"[ \t]+", " ", text)

    # 7. Collapse hơn 2 newlines liên tiếp → 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 8. Xóa trailing space cuối mỗi dòng, rồi strip toàn bộ
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines).strip()

    return Page(page_number=page.page_number, text=text)


def _remove_headers_footers(
    pages: list[Page],
    check_lines: int = 2,
) -> list[Page]:
    """
    Phát hiện các dòng xuất hiện giống nhau ở đầu hoặc cuối của >= 50% số trang,
    rồi xóa chúng khỏi từng trang.

    Ví dụ: "Trang 1 | Báo cáo năm 2024" xuất hiện ở bottom mọi trang → xóa.
    """
    threshold = max(2, len(pages) // 2)

    top_counter: Counter[str] = Counter()
    bottom_counter: Counter[str] = Counter()

    for page in pages:
        lines = [ln.strip() for ln in page.text.split("\n") if ln.strip()]
        for line in lines[:check_lines]:
            top_counter[line] += 1
        for line in lines[-check_lines:]:
            bottom_counter[line] += 1

    # Dòng lặp lại trên >= threshold trang → header/footer
    headers = {line for line, count in top_counter.items() if count >= threshold}
    footers = {line for line, count in bottom_counter.items() if count >= threshold}

    if not headers and not footers:
        return pages

    log.debug(
        "Detected repeated headers/footers",
        headers=list(headers),
        footers=list(footers),
    )

    result: list[Page] = []
    for page in pages:
        lines = page.text.split("\n")
        stripped = [ln.strip() for ln in lines]

        # Xóa header lines khỏi đầu trang
        start = 0
        while start < len(stripped) and stripped[start] in headers:
            start += 1

        # Xóa footer lines khỏi cuối trang
        end = len(stripped)
        while end > start and stripped[end - 1] in footers:
            end -= 1

        text = "\n".join(lines[start:end]).strip()
        result.append(Page(page_number=page.page_number, text=text))

    return result
