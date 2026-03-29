from backend.ingestion.chunker import chunk_pages
from backend.ingestion.loader import Page


def make_pages(text: str) -> list[Page]:
    return [Page(page_number=1, text=text)]


def test_short_text_single_chunk():
    pages = make_pages("Hello world")
    chunks = chunk_pages(pages, document_id="doc1", chunk_size=512, chunk_overlap=64)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world"
    assert chunks[0].document_id == "doc1"
    assert chunks[0].page_number == 1


def test_long_text_splits_into_multiple_chunks():
    long_text = "word " * 300  # 1500 chars
    pages = make_pages(long_text)
    chunks = chunk_pages(pages, document_id="doc2", chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 200  # allow some slack for word boundaries


def test_chunk_indices_sequential():
    pages = [Page(page_number=1, text="A " * 200), Page(page_number=2, text="B " * 200)]
    chunks = chunk_pages(pages, document_id="doc3", chunk_size=100, chunk_overlap=10)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_empty_pages_returns_no_chunks():
    chunks = chunk_pages([], document_id="doc4")
    assert chunks == []
