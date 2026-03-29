import json

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_session_id
from backend.api.schemas.chat import ChatRequest, ChatResponse, CitationSchema
from backend.pipeline import rag_pipeline, session_manager
from backend.retrieval.context_builder import Citation

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
log = structlog.get_logger()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session_id: str = Depends(get_session_id),
):
    sid = request.session_id or session_id
    result = await rag_pipeline.query(
        question=request.question,
        session_id=sid,
        document_ids=request.document_ids,
    )
    return ChatResponse(
        answer=result.answer,
        citations=[_citation_to_schema(c) for c in result.citations],
        session_id=sid,
    )


@router.get("/stream")
async def chat_stream(
    question: str,
    session_id: str = "default",
    document_ids: str | None = None,
):
    doc_ids = document_ids.split(",") if document_ids else None

    async def event_generator():
        citations: list[Citation] = []
        async for item in rag_pipeline.stream_query(
            question=question,
            session_id=session_id,
            document_ids=doc_ids,
        ):
            if isinstance(item, list):
                # Final item: citations
                citations = item
                payload = json.dumps([_citation_to_dict(c) for c in citations])
                yield f"event: citations\ndata: {payload}\n\n"
                yield "data: [DONE]\n\n"
            else:
                # Token
                yield f"data: {json.dumps(item)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/session/{sid}")
async def clear_session(sid: str):
    await session_manager.clear_session(sid)
    return {"message": f"Session {sid} cleared"}


def _citation_to_schema(c: Citation) -> CitationSchema:
    return CitationSchema(
        index=c.index,
        document_id=c.document_id,
        filename=c.filename,
        page_number=c.page_number,
        chunk_index=c.chunk_index,
        score=c.score,
        text=c.text,
    )


def _citation_to_dict(c: Citation) -> dict:
    return {
        "index": c.index,
        "document_id": c.document_id,
        "filename": c.filename,
        "page_number": c.page_number,
        "chunk_index": c.chunk_index,
        "score": c.score,
        "text": c.text,
    }
