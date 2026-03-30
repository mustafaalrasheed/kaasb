"""
Kaasb Platform - Security Middleware
Rate limiting, security headers, and request tracking.
"""

import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable

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
    """Redis-backed rate limiter with bounded in-memory fallback."""

    # Cap in-memory entries to prevent OOM from spoofed IPs
    _MAX_FALLBACK_KEYS = 10_000

    def __init__(self):
        self._fallback: dict = defaultdict(list)

    def _cleanup_fallback(self, now: float, window: int) -> None:
        """Evict expired entries and enforce max key count."""
        if len(self._fallback) > self._MAX_FALLBACK_KEYS:
            # Evict oldest entries beyond the cap
            expired_keys = [
                k for k, timestamps in self._fallback.items()
                if not timestamps or now - timestamps[-1] >= window
            ]
            for k in expired_keys:
                del self._fallback[k]
            # If still over limit, evict the oldest keys
            if len(self._fallback) > self._MAX_FALLBACK_KEYS:
                keys_to_remove = list(self._fallback.keys())[: len(self._fallback) - self._MAX_FALLBACK_KEYS]
                for k in keys_to_remove:
                    del self._fallback[k]

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
        # Fallback to in-memory sliding window (bounded)
        now = time.time()
        self._cleanup_fallback(now, window)
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
    "login": {"limit": 5, "window": 300},               # 5 per 5 min
    "register": {"limit": 3, "window": 600},             # 3 per 10 min
    "password_change": {"limit": 5, "window": 300},      # 5 per 5 min (brute-force protection)
    "password_reset": {"limit": 3, "window": 3600},      # 3 per hour (abuse prevention)
    "email_verification": {"limit": 3, "window": 3600},  # 3 per hour
    "upload": {"limit": 10, "window": 60},               # 10 per min
    "api_write": {"limit": 120, "window": 60},           # 120 writes per min
    "api_read": {"limit": 120, "window": 60},            # 120 reads per min
}


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP for rate limiting.
    Only trusts X-Forwarded-For in production (behind a known reverse proxy).
    In other environments, uses the direct socket address to prevent spoofing.
    """
    if settings.ENVIRONMENT == "production":
        # In production behind a trusted reverse proxy (nginx/ALB),
        # take the rightmost-but-one (client IP set by our proxy).
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Use the first IP (set by the outermost trusted proxy)
            ips = [ip.strip() for ip in forwarded.split(",")]
            # If there's only one proxy, take the first; otherwise take
            # the second-to-last (the one our edge proxy appended).
            return ips[0] if len(ips) == 1 else ips[-2]
    # In non-production or when no proxy header: use direct socket IP
    return request.client.host if request.client else "unknown"


def _get_rate_limit_tier(request: Request) -> str:
    """Determine which rate limit tier applies."""
    path = request.url.path
    method = request.method.upper()

    if "/auth/login" in path and method == "POST":
        return "login"
    if "/auth/register" in path and method == "POST":
        return "register"
    if "/users/password" in path and method == "PUT":
        return "password_change"
    if ("/auth/forgot-password" in path or "/auth/reset-password" in path) and method == "POST":
        return "password_reset"
    if ("/auth/resend-verification" in path or "/auth/verify-email" in path) and method == "POST":
        return "email_verification"
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
    WEBHOOK_PATHS: set = set()  # Qi Card uses browser redirects (GET), not server webhooks

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if settings.ENVIRONMENT == "development" or settings.ENVIRONMENT == "testing":
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
    """Add security headers and request timing to all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Track request timing for performance monitoring
        start_time = time.perf_counter()

        response = await call_next(request)

        # Add Server-Timing header — visible in browser DevTools and APM tools
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["Server-Timing"] = f"total;dur={duration_ms:.1f}"
        # Log slow requests (>1s) for investigation
        if duration_ms > 1000:
            logger.warning(
                "Slow request: %s %s took %.0fms [%s]",
                request.method, request.url.path, duration_ms, request_id,
            )

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
                "connect-src 'self' https://api.pay.qi.iq https://api.uat.pay.qi.iq; "
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
        # Skip rate limiting entirely in testing (CI runs all endpoints sequentially)
        if settings.ENVIRONMENT == "testing":
            return await call_next(request)

        # Skip rate limiting for health checks and static files
        path = request.url.path
        if path in ("/", "/health", "/docs", "/redoc", "/openapi.json") or path.startswith("/api/v1/health"):
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
