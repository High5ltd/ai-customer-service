import json

import redis.exceptions as redis_exc
import structlog

from RAG.config.settings import get_settings
from RAG.db.redis import get_redis_client
from RAG.exceptions import InfraUnavailableError

log = structlog.get_logger()

_REDIS_NET_ERRORS = (
    redis_exc.ConnectionError,
    redis_exc.TimeoutError,
    redis_exc.BusyLoadingError,
    ConnectionRefusedError,
    ConnectionResetError,
    BrokenPipeError,
)


def _session_key(session_id: str) -> str:
    return f"session:{session_id}:history"


async def get_history(session_id: str) -> list[dict]:
    try:
        client = get_redis_client()
        raw = await client.get(_session_key(session_id))
    except _REDIS_NET_ERRORS as e:
        raise InfraUnavailableError("Redis is unavailable.") from e
    if not raw:
        return []
    return json.loads(raw)


async def append_turn(session_id: str, role: str, content: str) -> None:
    settings = get_settings()
    try:
        client = get_redis_client()
        key = _session_key(session_id)

        history = await get_history(session_id)
        history.append({"role": role, "content": content})

        await client.set(key, json.dumps(history), ex=settings.redis_session_ttl)
    except InfraUnavailableError:
        raise
    except _REDIS_NET_ERRORS as e:
        raise InfraUnavailableError("Redis is unavailable.") from e


async def clear_session(session_id: str) -> None:
    try:
        client = get_redis_client()
        await client.delete(_session_key(session_id))
    except _REDIS_NET_ERRORS as e:
        raise InfraUnavailableError("Redis is unavailable.") from e
    log.info("Session cleared", session_id=session_id)
