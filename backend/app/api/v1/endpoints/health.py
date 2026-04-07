"""
Kaasb Platform - Health Check Endpoints

Three tiers designed for different consumers:
  /health        → Load balancer / uptime monitor (fast, lightweight)
  /health/ready  → Kubernetes/Docker readiness probe (must-pass before traffic)
  /health/detailed → Ops dashboard (auth-protected, full diagnostics + latencies)
"""

import contextlib
import logging
import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import engine, get_db
from app.middleware.monitoring import HEALTH_CHECK_FAILURES
from app.services.qi_card_client import QiCardClient

logger  = logging.getLogger(__name__)
router  = APIRouter(tags=["Health"])
settings = get_settings()

_bearer = HTTPBearer(auto_error=False)


# ─────────────────────────────────────────────────────────────────────────────
# GET /health  — lightweight liveness check
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health", summary="Liveness check")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Fast liveness probe.  Checks DB and Redis.
    Used by: Nginx upstream health check, UptimeRobot, Healthchecks.io.
    Returns 200 (healthy) or 503 (degraded).
    """
    db_ok    = await _check_db(db)
    redis_ok = await _check_redis()

    is_healthy = db_ok and redis_ok
    body = {
        "status":      "healthy" if is_healthy else "degraded",
        "app":         settings.APP_NAME,
        "version":     settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database":    "connected"    if db_ok    else "disconnected",
        "redis":       "connected"    if redis_ok else "disconnected",
    }
    return JSONResponse(content=body, status_code=200 if is_healthy else 503)


# ─────────────────────────────────────────────────────────────────────────────
# GET /health/ready  — readiness probe (traffic gate)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health/ready", summary="Readiness probe")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe — only returns 200 when the service is ready to accept traffic.
    Stricter than /health: also verifies DB schema is migrated.
    Used by: Docker healthcheck, Nginx upstream probe, deploy scripts.
    """
    db_ok    = await _check_db(db)
    redis_ok = await _check_redis()
    schema_ok = await _check_schema_migrated(db) if db_ok else False

    ready = db_ok and redis_ok and schema_ok
    return JSONResponse(
        content={
            "ready":     ready,
            "database":  db_ok,
            "redis":     redis_ok,
            "schema":    schema_ok,
        },
        status_code=200 if ready else 503,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /health/detailed  — full diagnostics (auth-protected, ops only)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health/detailed", summary="Detailed diagnostics (admin only)")
async def detailed_health(
    request: Request,
    db:      AsyncSession = Depends(get_db),
    creds:   HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    """
    Full diagnostics endpoint.  Auth-protected so external scanners can't
    enumerate internal service topology.

    Protected by: Bearer token matching HEALTH_BEARER_TOKEN env var.
    If no token is configured, endpoint is disabled in production.
    """
    if settings.ENVIRONMENT == "production":
        expected = getattr(settings, "HEALTH_BEARER_TOKEN", "")
        if not expected:
            raise HTTPException(status_code=404)   # Not advertised
        if not creds or creds.credentials != expected:
            raise HTTPException(status_code=401, detail="Unauthorized")

    results: dict = {}

    # ── Database ──────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    db_ok = await _check_db(db)
    db_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not db_ok:
        HEALTH_CHECK_FAILURES.labels(dependency="database").inc()

    # DB pool stats
    pool = engine.pool
    pool_info = {}
    with contextlib.suppress(Exception):
        pool_info = {
            "size":       pool.size(),
            "checked_out": pool.checkedout(),
            "overflow":   getattr(pool, "overflow", lambda: None)(),
            "invalid":    getattr(pool, "invalidated", lambda: None)(),
        }

    results["database"] = {
        "status":      "connected" if db_ok else "disconnected",
        "latency_ms":  db_ms,
        "pool":        pool_info,
    }

    # ── Redis ─────────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    redis_ok, redis_info = await _check_redis_detailed()
    redis_ms = round((time.perf_counter() - t0) * 1000, 1)
    if not redis_ok:
        HEALTH_CHECK_FAILURES.labels(dependency="redis").inc()

    results["redis"] = {
        "status":     "connected" if redis_ok else "disconnected",
        "latency_ms": redis_ms,
        **redis_info,
    }

    # ── Qi Card circuit breaker ───────────────────────────────────────────────
    qi_state = "unknown"
    if QiCardClient._circuit is not None:
        qi_state = QiCardClient._circuit.state.value
    if qi_state == "open":
        HEALTH_CHECK_FAILURES.labels(dependency="qi_card").inc()

    results["qi_card_circuit"] = qi_state

    # ── Alembic migration head ────────────────────────────────────────────────
    results["schema"] = {"migrated": await _check_schema_migrated(db)}

    # ── Summary ───────────────────────────────────────────────────────────────
    is_healthy = db_ok and redis_ok
    return JSONResponse(
        content={
            "status":      "healthy" if is_healthy else "degraded",
            "app":         settings.APP_NAME,
            "version":     settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "checks":      results,
        },
        status_code=200 if is_healthy else 503,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _check_db(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        return False


async def _check_redis() -> bool:
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        try:
            await r.ping()
            return True
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return False


async def _check_redis_detailed() -> tuple[bool, dict]:
    """Returns (ok, info_dict) with memory/keyspace stats."""
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        try:
            info = await r.info("memory")
            keyspace = await r.info("keyspace")
            return True, {
                "used_memory_human": info.get("used_memory_human"),
                "maxmemory_human":   info.get("maxmemory_human") or "no limit",
                "keyspace":          keyspace,
            }
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("Redis detailed check failed: %s", exc)
        return False, {}


async def _check_schema_migrated(db: AsyncSession) -> bool:
    """Verify the alembic_version table exists and has a head revision."""
    try:
        result = await db.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )
        row = result.fetchone()
        return row is not None
    except Exception:
        return False
