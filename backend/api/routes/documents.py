import asyncio
import mimetypes
import os
from pathlib import Path

import aiofiles
import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_db_session
from backend.api.schemas.document import DocumentResponse
from backend.config.settings import get_settings
from backend.db.repositories.document_repo import DocumentRepository
from backend.ingestion.pipeline import delete_document_vectors, ingest_document

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
log = structlog.get_logger()


@router.post("/upload", response_model=DocumentResponse, status_code=202)
async def upload_document(
    file: UploadFile,
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()
    max_bytes = settings.max_file_size_mb * 1024 * 1024

    # Validate file size
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb} MB.",
        )

    # Detect MIME type
    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "text/plain"

    # Save file to upload dir
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename or "upload").name
    dest_path = upload_dir / safe_name
    # Avoid overwriting — append suffix if needed
    counter = 1
    while dest_path.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        dest_path = upload_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    async with aiofiles.open(dest_path, "wb") as f:
        await f.write(content)

    # Run ingestion in background (non-blocking)
    doc = await ingest_document(
        file_path=dest_path,
        original_filename=file.filename or safe_name,
        mime_type=mime_type,
        file_size=len(content),
    )

    return DocumentResponse.model_validate(doc)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(session: AsyncSession = Depends(get_db_session)):
    repo = DocumentRepository(session)
    docs = await repo.list_all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, session: AsyncSession = Depends(get_db_session)):
    repo = DocumentRepository(session)
    doc = await repo.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str, session: AsyncSession = Depends(get_db_session)):
    repo = DocumentRepository(session)
    doc = await repo.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete vectors from Qdrant
    await delete_document_vectors(doc_id)

    # Delete file if exists
    settings = get_settings()
    file_path = Path(settings.upload_dir) / doc.filename
    if file_path.exists():
        file_path.unlink()

    # Delete DB record
    await repo.delete(doc_id)
