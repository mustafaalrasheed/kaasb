"""
Kaasb Platform - Main Application
FastAPI application factory with middleware, CORS, and lifecycle management.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import init_db, engine
from app.api.v1.router import api_router

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
    async def global_exception_handler(request, exc):
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
