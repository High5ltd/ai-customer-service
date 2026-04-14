"""
Direct chat completion (no RAG). Used by HTTP layer for livechat / integration tests.
"""

import structlog

from RAG.generation import llm_client

log = structlog.get_logger()

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful customer support assistant. "
    "Reply clearly and concisely in the same language as the user."
)


async def complete_direct_chat(
    *,
    query: str,
    system_prompt: str | None = None,
    temperature: float = 0.2,
) -> str:
    system = (system_prompt or "").strip() or DEFAULT_SYSTEM_PROMPT
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": query},
    ]
    answer = await llm_client.complete(messages, temperature=temperature)
    log.info("direct_llm.completed", query_len=len(query), answer_len=len(answer))
    return answer
