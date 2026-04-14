"""Map infrastructure failures to HTTP 503 for routes that need Postgres / Redis / Qdrant."""

import redis.exceptions as redis_exc
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DisconnectionError, InterfaceError, OperationalError

from RAG.exceptions import InfraUnavailableError

log = structlog.get_logger()

_DETAIL = "Required infrastructure (database, cache, or vector store) is unavailable."


async def _infra_handler(request: Request, exc: Exception) -> JSONResponse:
    log.warning(
        "infra.unavailable",
        exc_type=type(exc).__name__,
        path=str(request.url.path),
    )
    return JSONResponse(status_code=503, content={"detail": _DETAIL})


def register_infra_exception_handlers(app: FastAPI) -> None:
    for exc_type in (
        OperationalError,
        DisconnectionError,
        InterfaceError,
        redis_exc.ConnectionError,
        redis_exc.TimeoutError,
        redis_exc.BusyLoadingError,
        InfraUnavailableError,
    ):
        app.add_exception_handler(exc_type, _infra_handler)
