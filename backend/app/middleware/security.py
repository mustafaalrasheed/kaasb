"""
Kaasb Platform - Security Middleware
Rate limiting, security headers, and request tracking.
"""

import logging
import time
import uuid
from collections import defaultdict
from typing import Callable

import redis.asyncio as aioredis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# === Redis-backed Rate Limiter with in-memory fallback ===

_redis_client = None


async def _get_redis():
    """Return a shared Redis client, creating it lazily. Returns None on failure."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        except Exception:
            logger.warning("Redis unavailable for rate limiting; using in-memory fallback")
    return _redis_client


class RateLimiter:
    """Redis-backed rate limiter with in-memory fallback."""

    def __init__(self):
        self._fallback: dict = defaultdict(list)

    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Return True if the request is within the rate limit."""
        try:
            r = await _get_redis()
            if r:
                pipe = r.pipeline()
                pipe.incr(key)
                pipe.expire(key, window)
                results = await pipe.execute()
                count = results[0]
                return count <= limit
        except Exception:
            pass
        # Fallback to in-memory sliding window
        now = time.time()
        self._fallback[key] = [t for t in self._fallback[key] if now - t < window]
        if len(self._fallback[key]) >= limit:
            return False
        self._fallback[key].append(now)
        return True

    async def get_remaining(self, key: str, limit: int, window: int) -> int:
        """Return the number of remaining requests in the current window."""
        try:
            r = await _get_redis()
            if r:
                count = await r.get(key)
                return max(0, limit - int(count or 0))
        except Exception:
            pass
        now = time.time()
        recent = [t for t in self._fallback.get(key, []) if now - t < window]
        return max(0, limit - len(recent))


rate_limiter = RateLimiter()

# Rate limit tiers
RATE_LIMITS = {
    "login": {"limit": 5, "window": 300},       # 5 per 5 min
    "register": {"limit": 3, "window": 600},     # 3 per 10 min
    "upload": {"limit": 10, "window": 60},        # 10 per min
    "api_write": {"limit": 120, "window": 60},    # 120 writes per min
    "api_read": {"limit": 120, "window": 60},     # 120 reads per min
}


def _get_client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_rate_limit_tier(request: Request) -> str:
    """Determine which rate limit tier applies."""
    path = request.url.path
    method = request.method.upper()

    if "/auth/login" in path and method == "POST":
        return "login"
    if "/auth/register" in path and method == "POST":
        return "register"
    if "/avatar" in path and method == "POST":
        return "upload"
    if method in ("POST", "PUT", "DELETE", "PATCH"):
        return "api_write"
    return "api_read"


# === CSRF Origin Validation Middleware ===

class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Validate Origin/Referer on state-changing requests to prevent CSRF.
    Only enforced in production; development allows all origins.
    """

    UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}
    # Paths that receive external webhooks (no browser origin)
    WEBHOOK_PATHS = {"/api/v1/payments/qi-card/webhook"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if settings.ENVIRONMENT != "production":
            return await call_next(request)

        if request.method not in self.UNSAFE_METHODS:
            return await call_next(request)

        # Skip webhook endpoints (server-to-server, no Origin header)
        if request.url.path in self.WEBHOOK_PATHS:
            return await call_next(request)

        origin = request.headers.get("origin") or ""
        referer = request.headers.get("referer") or ""

        # Extract origin from referer if origin header is absent
        check_value = origin
        if not check_value and referer:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            check_value = f"{parsed.scheme}://{parsed.netloc}"

        if not check_value:
            return Response(
                content='{"detail":"Missing Origin header on state-changing request"}',
                status_code=403,
                media_type="application/json",
            )

        if check_value not in settings.CORS_ORIGINS:
            return Response(
                content='{"detail":"Origin not allowed"}',
                status_code=403,
                media_type="application/json",
            )

        return await call_next(request)


# === Security Headers Middleware ===

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        response = await call_next(request)

        # Security headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # HSTS in production
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content-Security-Policy
        if settings.ENVIRONMENT == "production":
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' https://api.stripe.com; "
                "frame-ancestors 'none'"
            )

        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]

        return response


# === Rate Limiting Middleware ===

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting based on endpoint tier."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and static files
        path = request.url.path
        if path in ("/", "/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)
        if path.startswith("/uploads/"):
            return await call_next(request)

        client_ip = _get_client_ip(request)
        tier = _get_rate_limit_tier(request)
        config = RATE_LIMITS[tier]

        rate_key = f"{tier}:{client_ip}"

        if not await rate_limiter.is_allowed(rate_key, config["limit"], config["window"]):
            retry_after = config["window"]
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(config["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        response = await call_next(request)

        # Add rate limit headers to response
        remaining = await rate_limiter.get_remaining(rate_key, config["limit"], config["window"])
        response.headers["X-RateLimit-Limit"] = str(config["limit"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
