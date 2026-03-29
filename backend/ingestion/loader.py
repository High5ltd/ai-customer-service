import io
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Page:
    page_number: int
    text: str


def load_file(file_path: str | Path, mime_type: str) -> list[Page]:
    path = Path(file_path)
    if mime_type == "application/pdf" or path.suffix.lower() == ".pdf":
        return _load_pdf(path)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ) or path.suffix.lower() in (".docx", ".doc"):
        return _load_docx(path)
    else:
        return _load_text(path)


def _load_pdf(path: Path) -> list[Page]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(Page(page_number=i + 1, text=text))
    return pages


def _load_docx(path: Path) -> list[Page]:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    # Treat entire DOCX as a single "page"
    text = "\n\n".join(paragraphs)
    return [Page(page_number=1, text=text)] if text else []


def _load_text(path: Path) -> list[Page]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return [Page(page_number=1, text=text)] if text else []
