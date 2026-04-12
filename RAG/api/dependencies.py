import uuid
from collections.abc import AsyncGenerator

from fastapi import Cookie, Header
from sqlalchemy.ext.asyncio import AsyncSession

from RAG.db.postgres import get_db_session as _get_db_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db_session():
        yield session


def get_session_id(
    x_session_id: str | None = Header(default=None),
    session_id: str | None = Cookie(default=None),
) -> str:
    return x_session_id or session_id or str(uuid.uuid4())
