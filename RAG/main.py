import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from RAG.api.router import router
from RAG.config.settings import get_settings
from RAG.db.postgres import close_engine, get_engine
from RAG.db.qdrant import close_qdrant_client, ensure_collection
from RAG.db.redis import close_redis_client, get_redis_client


def configure_logging(log_level: str) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    log = structlog.get_logger()
    log.info("Starting RAG service", port=settings.app_port)

    # Warm up connections
    get_engine()
    get_redis_client()
    await ensure_collection()
    log.info("All connections ready")

    yield

    # Shutdown
    await close_engine()
    await close_redis_client()
    await close_qdrant_client()
    log.info("RAG service stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="RAG Service",
        description="Retrieval-Augmented Generation API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    Instrumentator(
        excluded_handlers=["/metrics", "/health", "/health/ready"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return app


app = create_app()
