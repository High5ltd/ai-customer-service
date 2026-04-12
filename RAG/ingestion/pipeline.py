import uuid
from pathlib import Path

import structlog
from qdrant_client.models import PointStruct

from RAG.config.settings import get_settings
from RAG.db.models.document import Document
from RAG.db.postgres import get_session_factory
from RAG.db.qdrant import get_qdrant_client
from RAG.db.repositories.document_repo import DocumentRepository
from RAG.ingestion.chunker import chunk_pages
from RAG.ingestion.embedder import embed_chunks
from RAG.ingestion.loader import load_file
from RAG.ingestion.preprocessor import preprocess_pages

log = structlog.get_logger()


async def ingest_document(
    file_path: str | Path,
    original_filename: str,
    mime_type: str,
    file_size: int,
) -> Document:
    settings = get_settings()
    doc_id = str(uuid.uuid4())

    factory = get_session_factory()
    async with factory() as session:
        repo = DocumentRepository(session)

        # Create document record with processing status
        doc = await repo.create(
            id=doc_id,
            filename=Path(file_path).name,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size=file_size,
            status="processing",
        )
        log.info("Document created", doc_id=doc_id, filename=original_filename)

        try:
            # Load text from file
            pages = load_file(file_path, mime_type)
            if not pages:
                raise ValueError("No text extracted from document")

            # Preprocess pages: normalize, clean, remove headers/footers
            pages = preprocess_pages(
                pages,
                min_page_length=settings.preprocess_min_page_length,
                detect_headers_footers=settings.preprocess_detect_headers_footers,
                header_footer_lines=settings.preprocess_header_footer_lines,
            )
            if not pages:
                raise ValueError("No usable content after preprocessing")
            log.info("Pages preprocessed", doc_id=doc_id, page_count=len(pages))

            # Chunk the pages
            chunks = chunk_pages(
                pages,
                document_id=doc_id,
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
            log.info("Document chunked", doc_id=doc_id, chunk_count=len(chunks))

            # Embed the chunks
            embedded = await embed_chunks(chunks)

            # Upsert into Qdrant
            qdrant = get_qdrant_client()
            points = [
                PointStruct(
                    id=f"{doc_id}_{ec.chunk.chunk_index}",
                    vector=ec.vector,
                    payload={
                        "document_id": doc_id,
                        "chunk_index": ec.chunk.chunk_index,
                        "text": ec.chunk.text,
                        "page_number": ec.chunk.page_number,
                        "filename": original_filename,
                    },
                )
                for ec in embedded
            ]
            await qdrant.upsert(
                collection_name=settings.qdrant_collection,
                points=points,
            )
            log.info("Vectors upserted", doc_id=doc_id, count=len(points))

            # Update document status to ready
            doc = await repo.update_status(doc_id, "ready", chunk_count=len(chunks))

        except Exception as exc:
            log.error("Ingestion failed", doc_id=doc_id, error=str(exc))
            doc = await repo.update_status(doc_id, "failed", error_message=str(exc))

        return doc


async def delete_document_vectors(doc_id: str) -> None:
    settings = get_settings()
    qdrant = get_qdrant_client()
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    await qdrant.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=doc_id))]
        ),
    )
    log.info("Vectors deleted", doc_id=doc_id)
