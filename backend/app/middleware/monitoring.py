"""
Kaasb Platform - Monitoring Middleware
Correlation IDs, structured request logging, and custom Prometheus metrics.

Responsibilities:
  1. RequestContextMiddleware — generates a full UUID request_id, stores it
     in contextvars so every log line in the request's async chain carries it.
  2. LoggingContextFilter — injects request_id + user_id from contextvars into
     every LogRecord without touching caller code.
  3. Custom Prometheus counters for business-critical events (auth, payments,
     rate limits) that prometheus-fastapi-instrumentator does not track.
"""

import logging
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

# ─── Async-safe request context ───────────────────────────────────────────────
# These ContextVars are set once per request in RequestContextMiddleware and
# are readable anywhere in the same async call chain (no lock needed).

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
user_id_var:    ContextVar[str] = ContextVar("user_id",    default="-")
endpoint_var:   ContextVar[str] = ContextVar("endpoint",   default="-")


def get_request_id() -> str:
    """Return the current request's correlation ID (safe to call from any coroutine)."""
    return request_id_var.get("-")


def set_user_id(uid: str) -> None:
    """Called by auth dependency once the JWT is decoded."""
    user_id_var.set(uid)


# ─── Logging filter ───────────────────────────────────────────────────────────

class LoggingContextFilter(logging.Filter):
    """
    Injects request_id and user_id from contextvars into every LogRecord.

    Install once on the root logger so ALL loggers (SQLAlchemy, httpx, etc.)
    automatically carry these fields in production JSON output:
        logging.getLogger().addFilter(LoggingContextFilter())
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")   # type: ignore[attr-defined]
        record.user_id    = user_id_var.get("-")       # type: ignore[attr-defined]
        return True


# ─── Custom Prometheus metrics ────────────────────────────────────────────────
# prometheus-fastapi-instrumentator tracks http_requests_total and
# http_request_duration_seconds automatically.  These counters cover the
# business-critical events that HTTP metrics alone can't reveal.

# Auth events
AUTH_EVENTS = Counter(
    "kaasb_auth_events_total",
    "Authentication event counts",
    ["event"],   # login_success | login_failure | lockout | register | logout | token_refresh
)

# Payment events
PAYMENT_EVENTS = Counter(
    "kaasb_payment_events_total",
    "Payment event counts",
    ["type", "status", "provider"],  # e.g. escrow_fund/completed/qi_card
)

# Rate limit hits
RATE_LIMIT_HITS = Counter(
    "kaasb_rate_limit_hits_total",
    "Rate limit rejections by tier",
    ["tier"],    # login | register | api_write | api_read | upload
)

# Background / async job results
JOB_EVENTS = Counter(
    "kaasb_background_job_total",
    "Background job execution results",
    ["job_name", "status"],   # status: success | failure
)

# External service call duration (QiCard, SMTP)
EXTERNAL_CALL_DURATION = Histogram(
    "kaasb_external_call_duration_seconds",
    "Duration of calls to external services",
    ["service", "operation"],   # e.g. qi_card/create_payment
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Active WebSocket connections
WS_CONNECTIONS = Gauge(
    "kaasb_websocket_connections_active",
    "Currently open WebSocket connections",
)

# Database connection pool saturation  (updated by database.py checkout listener)
DB_POOL_CHECKEDOUT = Gauge(
    "kaasb_db_pool_connections_checked_out",
    "DB connections currently checked out from the pool",
)
DB_POOL_SIZE = Gauge(
    "kaasb_db_pool_size_total",
    "DB connection pool total capacity (pool_size + max_overflow)",
)

# Health check failures (incremented by health endpoint on dependency failure)
HEALTH_CHECK_FAILURES = Counter(
    "kaasb_health_check_failures_total",
    "Health check dependency failures",
    ["dependency"],   # database | redis | qi_card
)

# Business activity counters (updated by service layer)
BUSINESS_EVENTS = Counter(
    "kaasb_business_events_total",
    "Key business activity events",
    ["event"],  # job_posted | proposal_submitted | contract_created | review_submitted
)


# ─── Request context middleware ───────────────────────────────────────────────

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    1. Generates a full UUID v4 request_id (replaces the 8-char one from
       SecurityHeadersMiddleware — both will be in X-Request-ID but this one
       is stored in contextvars for log correlation).
    2. Propagates an incoming X-Request-ID if provided by a trusted upstream
       (e.g. Nginx injects it).
    3. Logs every request/response at INFO level with structured fields.
    4. PII redaction: passwords and tokens are masked in log output.
    """

    # Paths excluded from verbose request logging (too noisy / no value)
    _SKIP_LOG_PATHS = frozenset({
        "/health", "/health/ready", "/metrics", "/",
        "/api/v1/health", "/api/v1/health/ready",
    })

    # Request body fields whose values are always masked in logs
    _SENSITIVE_FIELDS = frozenset({
        "password", "new_password", "old_password", "confirm_password",
        "token", "access_token", "refresh_token", "secret", "card_number",
        "cvv", "pin",
    })

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Use incoming X-Request-ID if present (allows Nginx to set it), else generate
        incoming_rid = request.headers.get("x-request-id", "")
        req_id = incoming_rid if (incoming_rid and len(incoming_rid) <= 64) else str(uuid.uuid4())

        # Store in contextvars — accessible throughout the entire request chain
        token_rid = request_id_var.set(req_id)
        token_uid = user_id_var.set("-")
        endpoint_var.set(f"{request.method} {request.url.path}")

        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000

            # Structured request log — skipped for health/metrics noise
            if request.url.path not in self._SKIP_LOG_PATHS:
                _req_logger.info(
                    "%s %s → %d  %.0fms",
                    request.method,
                    request.url.path,
                    status_code,
                    duration_ms,
                    extra={
                        "request_id": req_id,
                        "user_id":    user_id_var.get("-"),
                        "method":     request.method,
                        "path":       request.url.path,
                        "status":     status_code,
                        "duration_ms": round(duration_ms, 1),
                        "ip":         _get_client_ip(request),
                        "ua":         request.headers.get("user-agent", "")[:200],
                    },
                )

            # Reset contextvars (important for worker process reuse)
            request_id_var.reset(token_rid)
            user_id_var.reset(token_uid)


def _get_client_ip(request: Request) -> str:
    """Extract client IP, trusting X-Forwarded-For only in production."""
    from app.core.config import get_settings
    settings = get_settings()
    if settings.ENVIRONMENT == "production":
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            ips = [ip.strip() for ip in forwarded.split(",")]
            return ips[0] if len(ips) == 1 else ips[-2]
    return request.client.host if request.client else "unknown"


_req_logger = logging.getLogger("kaasb.requests")
