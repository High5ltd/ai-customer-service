import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.db.postgres import get_engine
from backend.db.qdrant import get_qdrant_client
from backend.db.redis import get_redis_client

router = APIRouter(tags=["health"])
log = structlog.get_logger()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready():
    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Qdrant
    try:
        client = get_qdrant_client()
        await client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    # Redis
    try:
        redis = get_redis_client()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse(
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
        status_code=status_code,
    )
