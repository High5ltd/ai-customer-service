from collections.abc import AsyncGenerator

import structlog
from openai import AsyncOpenAI

from backend.config.settings import get_settings
from backend.ingestion.embedder import get_openai_client

log = structlog.get_logger()


async def complete(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
) -> str:
    settings = get_settings()
    client = get_openai_client()
    chosen_model = model or settings.openai_chat_model

    response = await client.chat.completions.create(
        model=chosen_model,
        messages=messages,
        temperature=temperature,
        stream=False,
    )
    return response.choices[0].message.content or ""


async def stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
) -> AsyncGenerator[str, None]:
    settings = get_settings()
    client = get_openai_client()
    chosen_model = model or settings.openai_chat_model

    async with await client.chat.completions.create(
        model=chosen_model,
        messages=messages,
        temperature=temperature,
        stream=True,
    ) as response:
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
