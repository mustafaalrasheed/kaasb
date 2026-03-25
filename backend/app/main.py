"""
Kaasb Platform - Main Application
FastAPI application factory with middleware, CORS, security, and lifecycle management.
"""

import asyncio
import json
import logging
import logging.handlers
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine, init_db
from app.middleware.security import CSRFMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware

settings = get_settings()


class _JsonFormatter(logging.Formatter):
    """JSON log formatter for production — one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Propagate any extra fields attached via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in payload:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def _configure_logging() -> None:
    """Configure structured logging based on environment."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "production":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)-8s [%(name)s] %(message)s"))

    logging.basicConfig(level=log_level, handlers=[handler], force=True)

    # Quiet noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


_configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    - Startup: Initialize database tables (dev only)
    - Shutdown: Close database connections
    """
    # === Startup ===
    # Retry DB connection on startup — containers often start before postgres is ready
    for attempt in range(1, 6):
        try:
            from sqlalchemy import text as _text
            async with engine.connect() as conn:
                await conn.execute(_text("SELECT 1"))
            break
        except Exception as exc:
            if attempt == 5:
                logger.exception("Database unreachable after 5 attempts — aborting startup")
                raise
            wait = 2 ** attempt
            logger.warning("DB not ready (attempt %d/5): %s — retrying in %ds", attempt, exc, wait)
            await asyncio.sleep(wait)

    if settings.ENVIRONMENT == "development":
        await init_db()

    logger.info(
        "%s v%s started in %s mode",
        settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT,
    )

    yield

    # === Shutdown ===
    await engine.dispose()
    logger.info("%s shutting down...", settings.APP_NAME)


def create_app() -> FastAPI:
    """Application factory."""

    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description=(
            "Kaasb is a freelancing platform connecting talented freelancers "
            "with clients worldwide. Built with FastAPI and modern best practices."
        ),
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # === Middleware Stack (order matters: last added = first executed) ===

    # 1. CORS (outermost — must handle preflight before anything else)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Authorization", "Content-Type", "Accept",
            "Origin", "X-Requested-With", "X-Request-ID",
        ],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Limit"],
        max_age=3600,  # Cache preflight for 1 hour (was 10min — reduces OPTIONS requests by ~6x)
    )

    # 2. GZip compression (responses > 500 bytes)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # 3. CSRF origin validation
    app.add_middleware(CSRFMiddleware)

    # 4. Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # 5. Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # === Domain Exception → HTTP Response Mapping ===
    from app.core.exceptions import (
        BadRequestError,
        ConflictError,
        ExternalServiceError,
        ForbiddenError,
        NotFoundError,
        RateLimitError,
        UnauthorizedError,
    )

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"detail": exc.message})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request, exc: ForbiddenError):
        return JSONResponse(status_code=403, content={"detail": exc.message})

    @app.exception_handler(BadRequestError)
    async def bad_request_handler(request, exc: BadRequestError):
        return JSONResponse(status_code=400, content={"detail": exc.message})

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=401,
            content={"detail": exc.message},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(request, exc: RateLimitError):
        return JSONResponse(status_code=429, content={"detail": exc.message})

    @app.exception_handler(ExternalServiceError)
    async def external_service_handler(request, exc: ExternalServiceError):
        return JSONResponse(status_code=502, content={"detail": exc.message})

    # === Global Exception Handler ===
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(
            "Unhandled exception on %s %s: %s",
            request.method, request.url, exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # === Routes ===
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # === Static Files (uploaded avatars, etc.) ===
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

    # === Root endpoint ===
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "api": settings.API_PREFIX,
        }

    return app


# Create the app instance
app = create_app()
