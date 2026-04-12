from collections.abc import AsyncGenerator
from dataclasses import dataclass

import structlog

from RAG.generation import llm_client, prompts, response_parser
from RAG.ingestion.embedder import embed_text
from RAG.pipeline import session_manager
from RAG.retrieval import reranker, searcher
from RAG.retrieval.context_builder import Citation, build_context

log = structlog.get_logger()


@dataclass
class ChatResult:
    answer: str
    citations: list[Citation]
    session_id: str


async def query(
    question: str,
    session_id: str,
    document_ids: list[str] | None = None,
) -> ChatResult:
    # Embed question
    query_vector = await embed_text(question)

    # Retrieve and rerank
    results = await searcher.search(query_vector, document_ids=document_ids)
    ranked = reranker.rerank(results)

    # Build context
    ctx = build_context(ranked)

    # Load history
    history = await session_manager.get_history(session_id)

    # Build messages and generate
    messages = prompts.build_messages(question, ctx.context_text, history)
    answer = await llm_client.complete(messages)

    # Parse citations
    used_citations = response_parser.extract_used_citations(answer, ctx.citations)

    # Save turn to history
    await session_manager.append_turn(session_id, "user", question)
    await session_manager.append_turn(session_id, "assistant", answer)

    return ChatResult(answer=answer, citations=used_citations, session_id=session_id)


async def stream_query(
    question: str,
    session_id: str,
    document_ids: list[str] | None = None,
) -> AsyncGenerator[str | list[Citation], None]:
    # Embed question
    query_vector = await embed_text(question)

    # Retrieve and rerank
    results = await searcher.search(query_vector, document_ids=document_ids)
    ranked = reranker.rerank(results)

    # Build context
    ctx = build_context(ranked)

    # Load history
    history = await session_manager.get_history(session_id)

    # Build messages
    messages = prompts.build_messages(question, ctx.context_text, history)

    # Stream tokens, collect full answer
    full_answer = ""
    async for token in llm_client.stream(messages):
        full_answer += token
        yield token

    # Parse citations and yield as final item
    used_citations = response_parser.extract_used_citations(full_answer, ctx.citations)

    # Save to history
    await session_manager.append_turn(session_id, "user", question)
    await session_manager.append_turn(session_id, "assistant", full_answer)

    # Yield citations as the sentinel value
    yield used_citations
