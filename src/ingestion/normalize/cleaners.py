"""
Text Cleaners — Bước normalize trong pipeline B → C

Các hàm thuần túy (pure functions), không có dependency vào RAG package.
Input/output đều là str hoặc list[str].
"""

import re
import unicodedata
from collections import Counter


def clean_text(text: str) -> str:
    """
    Làm sạch một đoạn text thô từ PDF/DOCX/HTML.

    Thứ tự các bước quan trọng — không đổi thứ tự tuỳ tiện.
    """
    # 1. Unicode normalization: ﬁ→fi, ²→2, –→-, …→...
    text = unicodedata.normalize("NFKC", text)

    # 2. Xóa control characters (giữ \n=0x0A, \t=0x09, \r=0x0D)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

    # 3. Xóa soft hyphen (U+00AD) — ký tự không in được, gây nhiễu embedding
    text = text.replace("\u00ad", "")

    # 4. Chuẩn hóa line endings → \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 5. Fix hyphenated line breaks: "busi-\nness" → "business"
    text = re.sub(r"-\n(\w)", r"\1", text)

    # 6. Collapse nhiều space/tab liên tiếp → 1 space (không đụng \n)
    text = re.sub(r"[ \t]+", " ", text)

    # 7. Collapse > 2 newlines liên tiếp → 2 newlines (giữ paragraph break)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 8. Xóa trailing whitespace cuối mỗi dòng
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    return text.strip()


def detect_headers_footers(pages_text: list[str], check_lines: int = 2) -> tuple[set[str], set[str]]:
    """
    Phát hiện header và footer lặp lại qua các trang.

    Trả về (headers, footers) — tập các dòng cần xóa.
    Chỉ có ý nghĩa khi document có >= 3 trang.
    """
    if len(pages_text) < 3:
        return set(), set()

    threshold = max(2, len(pages_text) // 2)
    top_counter: Counter[str] = Counter()
    bottom_counter: Counter[str] = Counter()

    for text in pages_text:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        for line in lines[:check_lines]:
            top_counter[line] += 1
        for line in lines[-check_lines:]:
            bottom_counter[line] += 1

    headers = {line for line, count in top_counter.items() if count >= threshold}
    footers = {line for line, count in bottom_counter.items() if count >= threshold}

    return headers, footers


def remove_headers_footers(text: str, headers: set[str], footers: set[str]) -> str:
    """Xóa header/footer đã phát hiện ra khỏi một trang."""
    if not headers and not footers:
        return text

    lines = text.split("\n")
    stripped = [ln.strip() for ln in lines]

    start = 0
    while start < len(stripped) and stripped[start] in headers:
        start += 1

    end = len(stripped)
    while end > start and stripped[end - 1] in footers:
        end -= 1

    return "\n".join(lines[start:end]).strip()


def detect_language(text: str) -> str:
    """
    Phát hiện ngôn ngữ dựa trên ký tự đặc trưng.
    Không cần thư viện ngoài — đủ dùng cho bước phân loại cơ bản.

    Trả về: "vi", "de", "en", hoặc "unknown"
    """
    # Ký tự đặc trưng tiếng Việt (dấu thanh, dấu mũ, v.v.)
    vi_chars = set("àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ"
                   "ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐƠƯẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỴỶỸ")
    # Ký tự đặc trưng tiếng Đức (umlaut)
    de_chars = set("äöüÄÖÜß")

    sample = text[:2000]
    vi_count = sum(1 for c in sample if c in vi_chars)
    de_count = sum(1 for c in sample if c in de_chars)

    if vi_count > 10:
        return "vi"
    if de_count > 5:
        return "de"
    if any(c.isalpha() for c in sample):
        return "en"
    return "unknown"


def is_heading_line(line: str) -> bool:
    """
    Heuristic phát hiện heading trong text PDF.

    Heading thường là:
    - Dòng ngắn (< 80 ký tự)
    - Không kết thúc bằng dấu câu thông thường
    - Không phải số trang đơn thuần
    """
    stripped = line.strip()
    if not stripped:
        return False
    if len(stripped) > 80:
        return False
    # Không phải heading nếu kết thúc bằng dấu câu văn xuôi
    if stripped[-1] in ".,:;!?":
        return False
    # Không phải heading nếu là số đơn thuần (page number)
    if re.fullmatch(r"\d+", stripped):
        return False
    # Heading mạnh: toàn chữ hoa, có ít nhất 2 từ hoặc >= 4 ký tự
    if stripped.isupper() and len(stripped) >= 4:
        return True
    # Heading yếu: dòng ngắn, bắt đầu bằng số thứ tự (1. / 1.1 / Article 1)
    if re.match(r"^(\d+\.)+\s+\w", stripped):
        return True
    if re.match(r"^(Chapter|Section|Article|Part|Phần|Chương|Mục)\s+", stripped, re.IGNORECASE):
        return True

    return False
