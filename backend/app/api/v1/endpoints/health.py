"""
Kaasb Platform - Health Check Endpoint
"""

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.services.qi_card_client import QiCardClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", summary="Health check")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check if the API, database, Redis, and external services are running."""
    # Database check
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Redis check
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        try:
            await r.ping()
            redis_status = "connected"
        finally:
            await r.aclose()
    except Exception:
        redis_status = "disconnected"

    # Qi Card circuit breaker state (informational — does not affect overall health)
    qi_card_circuit = "unknown"
    if QiCardClient._circuit is not None:
        qi_card_circuit = QiCardClient._circuit.state.value

    is_healthy = db_status == "connected" and redis_status == "connected"
    overall = "healthy" if is_healthy else "degraded"

    body = {
        "status": overall,
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "redis": redis_status,
        "qi_card_circuit": qi_card_circuit,
    }

    # Return 503 so load balancers / uptime monitors can detect degraded state
    status_code = 200 if is_healthy else 503
    return JSONResponse(content=body, status_code=status_code)
