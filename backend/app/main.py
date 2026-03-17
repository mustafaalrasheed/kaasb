"""
Kaasb Platform - Main Application
FastAPI application factory with middleware, CORS, security, and lifecycle management.
"""

from contextlib import asynccontextmanager
from pathlib import Path

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import init_db, engine
from app.api.v1.router import api_router
from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware

logger = logging.getLogger(__name__)
settings = get_settings()


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
        print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started in {settings.ENVIRONMENT} mode")

    yield

    # === Shutdown ===
    await engine.dispose()
    print(f"👋 {settings.APP_NAME} shutting down...")


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
        max_age=600,  # Cache preflight for 10 minutes
    )

    # 2. GZip compression (responses > 500 bytes)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # 3. Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # === Global Exception Handler ===
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(
            f"Unhandled exception on {request.method} {request.url}: {exc}",
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
