"""
Kaasb Platform - Security Middleware
Rate limiting, security headers, and request tracking.
"""

import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

settings = get_settings()


# === In-Memory Rate Limiter (swap to Redis in production) ===

class RateLimiter:
    """Simple sliding-window rate limiter. Production: swap to Redis."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, key: str, window: int):
        now = time.time()
        self._requests[key] = [
            t for t in self._requests[key] if now - t < window
        ]

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """Check if request is within rate limit. Window in seconds."""
        self._cleanup(key, window)
        if len(self._requests[key]) >= limit:
            return False
        self._requests[key].append(time.time())
        return True

    def get_remaining(self, key: str, limit: int, window: int = 60) -> int:
        self._cleanup(key, window)
        return max(0, limit - len(self._requests[key]))


rate_limiter = RateLimiter()

# Rate limit tiers
RATE_LIMITS = {
    "login": {"limit": 5, "window": 300},       # 5 per 5 min
    "register": {"limit": 3, "window": 600},     # 3 per 10 min
    "upload": {"limit": 10, "window": 60},        # 10 per min
    "api_write": {"limit": 30, "window": 60},     # 30 writes per min
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

        if not rate_limiter.is_allowed(rate_key, config["limit"], config["window"]):
            remaining = 0
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
        remaining = rate_limiter.get_remaining(rate_key, config["limit"], config["window"])
        response.headers["X-RateLimit-Limit"] = str(config["limit"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
