"""
Kaasb Platform - Main Application
FastAPI application factory with middleware, CORS, and lifecycle management.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.database import init_db, engine
from app.core.limiter import limiter
from app.api.v1.router import api_router

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# === Security Headers Middleware ===

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard HTTP security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    - Startup: Initialize database tables (dev only)
    - Shutdown: Close database connections
    """
    # === Startup ===
    if settings.ENVIRONMENT == "development":
        await init_db()
        logger.info(
            "%s v%s started in %s mode",
            settings.APP_NAME,
            settings.APP_VERSION,
            settings.ENVIRONMENT,
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

    # === Rate Limiter ===
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # === Security Headers (added first so it wraps all responses) ===
    app.add_middleware(SecurityHeadersMiddleware)

    # === CORS Middleware ===
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # === Global Exception Handler ===
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception: %s %s",
            request.method,
            request.url,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error"
                if not settings.DEBUG
                else str(exc)
            },
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
