import json

import structlog

from RAG.config.settings import get_settings
from RAG.db.redis import get_redis_client

log = structlog.get_logger()


def _session_key(session_id: str) -> str:
    return f"session:{session_id}:history"


async def get_history(session_id: str) -> list[dict]:
    client = get_redis_client()
    raw = await client.get(_session_key(session_id))
    if not raw:
        return []
    return json.loads(raw)


async def append_turn(session_id: str, role: str, content: str) -> None:
    settings = get_settings()
    client = get_redis_client()
    key = _session_key(session_id)

    history = await get_history(session_id)
    history.append({"role": role, "content": content})

    await client.set(key, json.dumps(history), ex=settings.redis_session_ttl)


async def clear_session(session_id: str) -> None:
    client = get_redis_client()
    await client.delete(_session_key(session_id))
    log.info("Session cleared", session_id=session_id)
