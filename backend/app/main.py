"""
Kaasb Platform - Main Application
FastAPI application factory with middleware, CORS, security, and lifecycle management.
"""

import asyncio
import json
import logging
import logging.handlers
import sys
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine, init_db
from app.middleware.monitoring import LoggingContextFilter, RequestContextMiddleware
from app.middleware.security import CSRFMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware

settings = get_settings()


class _JsonFormatter(logging.Formatter):
    """
    JSON log formatter for production — one JSON object per line.
    Includes request_id and user_id from contextvars (set by RequestContextMiddleware)
    when the LoggingContextFilter is installed on the root logger.
    """

    # Fields on LogRecord that we never want to expose in JSON output
    _SKIP = frozenset(logging.LogRecord.__dict__)

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts":      self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        # Correlation IDs injected by LoggingContextFilter
        if rid := getattr(record, "request_id", None):
            payload["request_id"] = rid
        if uid := getattr(record, "user_id", None):
            payload["user_id"] = uid
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Propagate any extra fields attached via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key not in self._SKIP and key not in payload:
                try:
                    json.dumps(value)   # skip non-serialisable extras
                    payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = str(value)
        return json.dumps(payload, ensure_ascii=False)


def _configure_logging() -> None:
    """Configure structured logging based on environment."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "production":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(levelname)-8s [%(name)s] [%(request_id)s] %(message)s")
        )

    logging.basicConfig(level=log_level, handlers=[handler], force=True)

    # Install correlation-ID filter on the root logger so EVERY logger
    # (SQLAlchemy, httpx, third-party libs) automatically carries request_id.
    logging.getLogger().addFilter(LoggingContextFilter())

    # Quiet noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def _configure_sentry() -> None:
    """Initialise Sentry SDK if DSN is configured."""
    if not settings.SENTRY_DSN:
        return

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=f"kaasb@{settings.APP_VERSION}",
        # Capture 100% of errors, 10% of transactions for performance tracing
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        # Capture 20% of profiling sessions
        profiles_sample_rate=0.2 if settings.ENVIRONMENT == "production" else 0.0,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.INFO,        # Capture INFO and above as breadcrumbs
                event_level=logging.ERROR, # Send ERROR+ as Sentry events
            ),
        ],
        # Never send raw passwords, tokens, or card numbers to Sentry
        send_default_pii=False,
        before_send=_sentry_scrub_event,
    )


_SENTRY_SCRUB_KEYS = frozenset({
    "password", "new_password", "old_password", "confirm_password",
    "token", "access_token", "refresh_token", "secret_key",
    "authorization", "cookie", "card_number", "cvv",
})


def _sentry_scrub_event(event: dict[str, object], hint: dict[str, object]) -> dict[str, object] | None:
    """Strip sensitive fields from Sentry events before they leave the server."""
    def _scrub(obj):
        if isinstance(obj, dict):
            return {
                k: "[Filtered]" if k.lower() in _SENTRY_SCRUB_KEYS else _scrub(v)
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_scrub(i) for i in obj]
        return obj
    return _scrub(event)


_configure_logging()
_configure_sentry()
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

    # Start Redis pub/sub subscriber for cross-worker WebSocket delivery
    from app.services.websocket_manager import manager as ws_manager
    subscriber_task = asyncio.create_task(ws_manager.start_redis_subscriber())

    # Register in-process domain event subscribers (chat → notifications + WS push)
    from app.services.message_subscribers import register_message_subscribers
    register_message_subscribers()

    # Start daily marketplace scheduler (seller levels, gig ranks, auto-complete,
    # buyer-request expiry). Redis-lock-coordinated so only one worker runs each job.
    from app.tasks import scheduler as marketplace_scheduler
    marketplace_scheduler.start()

    logger.info(
        "%s v%s started in %s mode",
        settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT,
    )

    yield

    # === Shutdown ===
    await marketplace_scheduler.stop()
    subscriber_task.cancel()
    # suppress is a sync CM — valid around `await`. async-with was a mypy error
    # because AbstractContextManager has no __aenter__; ruff SIM105 otherwise
    # flags the equivalent try/except/pass.
    with suppress(asyncio.CancelledError):
        await subscriber_task
    await engine.dispose()
    logger.info("%s shutting down...", settings.APP_NAME)


def create_app() -> FastAPI:
    """Application factory."""

    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        description=(
            "## Kaasb — Iraqi Freelancing Marketplace\n\n"
            "REST API for the Kaasb platform connecting Iraqi and MENA freelancers with clients.\n\n"
            "### Authentication\n"
            "All protected endpoints require a Bearer token in the `Authorization` header:\n"
            "```\nAuthorization: Bearer <access_token>\n```\n"
            "Obtain tokens via `POST /auth/login` or `POST /auth/register`.\n"
            "Access tokens expire after **30 minutes**. Use `POST /auth/refresh` to renew.\n\n"
            "### Rate Limits\n"
            "- Login: 5 req / 5 min\n"
            "- Register: 3 req / 10 min\n"
            "- Standard API: 120 req / min\n\n"
            "### Developer Resources\n"
            "- [Postman Collection](https://github.com/mustafaalrasheed/kaasb/blob/main/docs/api/postman_collection.json)\n"
            "- [Developer Guide](https://github.com/mustafaalrasheed/kaasb/blob/main/docs/api/developer_guide.md)\n"
            "- [Error Code Reference](https://github.com/mustafaalrasheed/kaasb/blob/main/docs/api/error_codes.md)\n"
        ),
        version=settings.APP_VERSION,
        contact={
            "name": "Kaasb Platform",
            "url": f"https://{settings.DOMAIN}",
            "email": "dev@kaasb.com",
        },
        license_info={
            "name": "Proprietary",
            "url": f"https://{settings.DOMAIN}/terms",
        },
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_tags=[
            {"name": "Health", "description": "Liveness and readiness probes"},
            {"name": "Authentication", "description": "Register, login, token management"},
            {"name": "Users", "description": "User profiles and account management"},
            {"name": "Jobs", "description": "Job postings — search, create, manage"},
            {"name": "Proposals", "description": "Freelancer proposals on job postings"},
            {"name": "Contracts & Milestones", "description": "Active contracts and milestone workflow"},
            {"name": "Payments", "description": "Escrow, payouts via Qi Card"},
            {"name": "Reviews & Ratings", "description": "Post-contract reviews and ratings"},
            {"name": "Messages", "description": "Direct messaging between users"},
            {"name": "Notifications", "description": "In-app notification management"},
            {"name": "Admin", "description": "Platform administration (admin role required)"},
            {"name": "GDPR", "description": "Data rights — export your data (Art. 15) or delete your account (Art. 17)"},
            {"name": "Moderation", "description": "Content moderation — report jobs, users, messages, and reviews"},
        ],
        lifespan=lifespan,
    )

    # === Prometheus /metrics endpoint ========================================
    # Instruments all HTTP routes automatically (request count, latency, status).
    # Expose BEFORE middleware stack so /metrics bypasses rate limiting.
    # In production, protect /metrics at the Nginx level (allow only monitoring IPs).
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health", "/health/ready"],
    ).instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,  # Don't show in Swagger docs
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

    # 3. Request context + structured request logging (innermost so it runs last,
    #    after security headers set the final request_id)
    app.add_middleware(RequestContextMiddleware)

    # 4. CSRF origin validation
    app.add_middleware(CSRFMiddleware)

    # 5. Security headers (sets X-Request-ID on response)
    app.add_middleware(SecurityHeadersMiddleware)

    # 6. Rate limiting
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
        body: dict[str, Any] = {"detail": exc.message}
        if isinstance(exc.details, dict):
            body.update(exc.details)
        return JSONResponse(status_code=403, content=body)

    @app.exception_handler(BadRequestError)
    async def bad_request_handler(request, exc: BadRequestError):
        body: dict[str, Any] = {"detail": exc.message}
        if isinstance(exc.details, dict):
            body.update(exc.details)
        return JSONResponse(status_code=400, content=body)

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
        from app.middleware.monitoring import get_request_id
        rid = get_request_id()
        logger.error(
            "Unhandled exception [%s] on %s %s: %s",
            rid, request.method, request.url, exc,
            exc_info=True,  # noqa: LOG014
        )
        # Surface request_id to client so they can reference it in support tickets
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": rid},
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
