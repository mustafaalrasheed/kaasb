"""
Kaasb Platform - Qi Card Payment Gateway Client

Based on the official WooCommerce plugin (woocommerce-qi-payments.php).

UAT endpoint  : https://api.uat.pay.qi.iq/api/v0/transactions/business/token
Production    : https://api.pay.qi.iq/api/v0/transactions/business/token

Authentication:
  Single header — Authorization: <api_key>  (raw key, no "Bearer" prefix)

Payment flow (redirect-based, no webhook):
  1. POST /api/v0/transactions/business/token  → returns data.link (redirect URL)
  2. Redirect user to data.link
  3. User completes payment on Qi Card portal
  4. Qi Card redirects browser to:
       successUrl?CartID=<orderId>   on success
       failureUrl?CartID=<orderId>   on failure
       cancelUrl?CartID=<orderId>    on cancel
  5. Your handler at successUrl confirms the payment in the database

Request body:
  {
    "order": {
      "amount": 50000,        // IQD, whole number
      "currency": "IQD",
      "orderId": "escrow-<uuid>"
    },
    "timestamp": "2026-03-28T12:00:00+00:00",  // ISO 8601
    "successUrl": "https://kaasb.com/api/v1/payments/qi-card/success",
    "failureUrl": "https://kaasb.com/api/v1/payments/qi-card/failure",
    "cancelUrl":  "https://kaasb.com/api/v1/payments/qi-card/cancel"
  }

Response:
  {
    "success": true,
    "data": {
      "link": "https://pay.qi.iq/..."   // redirect user here
    }
  }

Currency: IQD (Iraqi Dinar). 1 USD ≈ 1,310 IQD.

Idempotency:
  create_payment is wrapped in a Redis-backed link cache keyed by order_id.
  If the same order_id arrives within QI_CARD_IDEMPOTENCY_TTL_SEC (default
  900s) the cached link is returned without re-calling Qi Card. This protects
  against duplicate charges from browser double-clicks, retries after network
  hiccups, or concurrent requests reaching different Gunicorn workers. If
  Redis is unavailable the cache is skipped (fail-open) so payments still work.
"""

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import ClassVar

import httpx
import redis.asyncio as aioredis

from app.core.config import get_settings
from app.utils.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

# ---- Log-sanitization helpers -------------------------------------------------

_LOG_BODY_MAX_LEN = 300
# Any of these JSON field names, if present, will be redacted in log previews.
_SENSITIVE_FIELDS = ("api_key", "apiKey", "authorization", "password", "token", "secret")
_SENSITIVE_RE = re.compile(
    r'("(?:' + "|".join(_SENSITIVE_FIELDS) + r')"\s*:\s*)"[^"]*"',
    re.IGNORECASE,
)


def _safe_preview(body: str | None, max_len: int = _LOG_BODY_MAX_LEN) -> str:
    """Return a truncated, sensitive-field-redacted preview safe to emit to logs."""
    if not body:
        return "(empty)"
    redacted = _SENSITIVE_RE.sub(r'\1"***"', body)
    if len(redacted) <= max_len:
        return redacted
    return redacted[:max_len] + "...(truncated)"


# ---- Idempotency cache --------------------------------------------------------

_redis_client: aioredis.Redis | None = None
_inmem_cache: dict[str, tuple[dict, float]] = {}  # fallback for tests/dev with no Redis
_INMEM_CACHE_MAX = 1024


async def _get_redis() -> aioredis.Redis | None:
    """Lazily open a shared async Redis client; returns None if unreachable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        settings = get_settings()
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await _redis_client.ping()
    except Exception as exc:
        logger.warning("Qi Card idempotency cache disabled — Redis unreachable: %s", exc)
        _redis_client = None
    return _redis_client


class QiCardError(Exception):
    """Raised when the Qi Card API returns an error or network failure."""
    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        # Kept as an attribute for programmatic access by callers; the exception's
        # str() form deliberately excludes it so it never ends up in un-sanitized logs.
        self.response_body = response_body


class QiCardClient:
    """
    Async HTTP client for the Qi Card payment gateway (v0 API).

    Usage:
        client = QiCardClient()
        result = await client.create_payment(
            amount_iqd=196500,
            order_id="escrow-<uuid>",
            success_url="https://kaasb.com/api/v1/payments/qi-card/success",
            failure_url="https://kaasb.com/api/v1/payments/qi-card/failure",
            cancel_url="https://kaasb.com/api/v1/payments/qi-card/cancel",
        )
        # Redirect user to result["link"]
    """

    _circuit: ClassVar[CircuitBreaker | None] = None

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = (
            self.settings.QI_CARD_SANDBOX_URL
            if self.settings.QI_CARD_SANDBOX
            else self.settings.QI_CARD_BASE_URL
        )
        if QiCardClient._circuit is None:
            QiCardClient._circuit = CircuitBreaker(
                name="qi_card",
                failure_threshold=5,
                recovery_timeout=60.0,
                exceptions=(httpx.RequestError, QiCardError),
            )

    def _is_configured(self) -> bool:
        """True when the API key is set."""
        return bool(self.settings.QI_CARD_API_KEY)

    def _headers(self) -> dict:
        """Auth headers — Authorization is the raw API key, no prefix."""
        return {
            "Authorization": self.settings.QI_CARD_API_KEY,
            "Content-type": "application/json",
        }

    # =========================================================================
    # Idempotency cache — keyed by order_id
    # =========================================================================

    def _cache_key(self, order_id: str) -> str:
        return f"qi_card:link:{order_id}"

    async def _cache_get(self, order_id: str) -> dict | None:
        """Return a previously cached create_payment response, or None."""
        redis = await _get_redis()
        if redis is not None:
            try:
                raw = await redis.get(self._cache_key(order_id))
                return json.loads(raw) if raw else None
            except Exception as exc:
                logger.warning("Qi Card idempotency cache read failed: %s", exc)
                return None
        # In-memory fallback (bounded). Used only when Redis is unreachable —
        # e.g. unit tests. TTL is enforced by _inmem_expiry_sweep.
        now = datetime.now(UTC).timestamp()
        entry = _inmem_cache.get(order_id)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at < now:
            _inmem_cache.pop(order_id, None)
            return None
        return value

    async def _cache_set(self, order_id: str, value: dict, ttl_seconds: int) -> None:
        redis = await _get_redis()
        if redis is not None:
            try:
                await redis.setex(self._cache_key(order_id), ttl_seconds, json.dumps(value))
                return
            except Exception as exc:
                logger.warning("Qi Card idempotency cache write failed: %s", exc)
                # fall through to in-memory fallback
        if len(_inmem_cache) >= _INMEM_CACHE_MAX:
            # Crude eviction: drop ~10% of entries ordered by insertion.
            for k in list(_inmem_cache.keys())[: _INMEM_CACHE_MAX // 10]:
                _inmem_cache.pop(k, None)
        expires_at = datetime.now(UTC).timestamp() + ttl_seconds
        _inmem_cache[order_id] = (value, expires_at)

    # =========================================================================
    # Create Payment
    # =========================================================================

    @async_retry(max_attempts=3, base_delay=1.0, exceptions=(httpx.RequestError,))
    async def create_payment(
        self,
        amount_iqd: int,
        order_id: str,
        success_url: str,
        failure_url: str,
        cancel_url: str,
        currency: str = "IQD",
    ) -> dict:
        """
        Initiate a Qi Card payment.

        Idempotent per order_id within QI_CARD_IDEMPOTENCY_TTL_SEC: a repeat call
        within the window returns the cached link instead of re-calling Qi Card.

        Returns:
            {
                "link":       "https://pay.qi.iq/...",  # redirect user here
                "order_id":   "escrow-<uuid>",
                "amount_iqd": 196500,
            }
        """
        # Return the cached response if we've already created a link for this
        # order_id recently. This is the primary idempotency guarantee — even
        # double-clicks that reach different workers will get the same link.
        cached = await self._cache_get(order_id)
        if cached is not None:
            logger.info("Qi Card create_payment idempotent hit: order_id=%s", order_id)
            return cached

        if not self._is_configured():
            result = self._mock_create(amount_iqd, order_id)
            await self._cache_set(order_id, result, self.settings.QI_CARD_IDEMPOTENCY_TTL_SEC)
            return result

        payload = {
            "order": {
                "amount": amount_iqd,
                "currency": currency,
                "orderId": order_id,
            },
            "timestamp": datetime.now(UTC).isoformat(),
            "successUrl": success_url,
            "failureUrl": failure_url,
            "cancelUrl": cancel_url,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await self._circuit.call(  # type: ignore[union-attr]
                    http.post,
                    self.base_url,
                    json=payload,
                    headers=self._headers(),
                )
        except CircuitOpenError as e:
            raise QiCardError(f"Payment gateway unavailable: {e}") from e
        except httpx.RequestError as e:
            raise QiCardError(f"Network error reaching Qi Card: {e}") from e

        if response.status_code not in (200, 201):
            logger.error(
                "Qi Card create_payment failed: status=%s body=%s",
                response.status_code, _safe_preview(response.text),
            )
            raise QiCardError(
                "Qi Card rejected payment creation",
                status_code=response.status_code,
                response_body=response.text,
            )

        try:
            body = response.json()
        except ValueError as e:
            logger.error(
                "Qi Card returned non-JSON body: %s",
                _safe_preview(response.text),
            )
            raise QiCardError("Qi Card returned an invalid response") from e

        if not body.get("success"):
            logger.error(
                "Qi Card create_payment returned success=false: %s",
                _safe_preview(json.dumps(body)),
            )
            raise QiCardError(
                "Qi Card payment creation failed",
                status_code=response.status_code,
                response_body=response.text,
            )

        link = body.get("data", {}).get("link")
        if not link:
            logger.error(
                "Qi Card response missing data.link: %s",
                _safe_preview(json.dumps(body)),
            )
            raise QiCardError(
                "Qi Card response missing data.link",
                response_body=response.text,
            )

        logger.info(
            "Qi Card payment created: order_id=%s amount_iqd=%d",
            order_id, amount_iqd,
        )

        result = {
            "link": link,
            "order_id": order_id,
            "amount_iqd": amount_iqd,
        }
        await self._cache_set(order_id, result, self.settings.QI_CARD_IDEMPOTENCY_TTL_SEC)
        return result

    # =========================================================================
    # Refund Payment
    # =========================================================================
    #
    # Qi Card's v1 3DS API exposes a refund endpoint:
    #   POST https://{host}/api/v1/payment/{paymentId}/refund
    #   Auth: Basic (username:password) + X-Terminal-Id header
    #   Body: { requestId, amount, message, extParams? }
    #
    # This is a DIFFERENT product from the v0 redirect API used in
    # create_payment above (raw API key, no terminal ID). Wiring refunds
    # therefore requires:
    #   1. Confirming the merchant account is provisioned against the v1
    #      3DS API (or migrating the create flow to v1 first).
    #   2. New settings: QI_CARD_V1_HOST, QI_CARD_TERMINAL_ID,
    #      QI_CARD_BASIC_USER, QI_CARD_BASIC_PASSWORD.
    #   3. Persisting the v1 paymentId returned from create (which v0 does
    #      not currently surface) so we can pass it here.
    #
    # Until that migration is done, refunds are issued by an admin through
    # the Qi Card merchant portal after the dispute/refund decision; this
    # method raises so the caller falls back to that manual path.

    async def refund_payment(
        self,
        payment_id: str,
        amount_iqd: int,
        reason: str = "",
    ) -> dict:
        """
        Refund a previously completed Qi Card payment.

        Not yet wired — see the block comment above for the v1 3DS migration
        that unlocks this. Raises QiCardError so the caller reconciles manually.
        """
        logger.warning(
            "Qi Card refund requested for payment_id=%s amount_iqd=%d — "
            "v1 3DS refund not yet wired; falling back to manual merchant portal",
            payment_id, amount_iqd,
        )
        raise QiCardError(
            "Qi Card refunds are not yet wired to the v1 3DS API. "
            "Process manually through the Qi Card merchant portal.",
        )

    # =========================================================================
    # Mock helpers (used when QI_CARD_API_KEY is not set)
    # =========================================================================

    def _mock_create(self, amount_iqd: int, order_id: str) -> dict:
        mock_id = uuid.uuid4().hex[:12]
        logger.info(
            "[MOCK] Qi Card create_payment: order_id=%s amount_iqd=%d",
            order_id, amount_iqd,
        )
        return {
            "link": f"https://merchant.uat.pay.qi.iq/mock-pay/{mock_id}?orderId={order_id}",
            "order_id": order_id,
            "amount_iqd": amount_iqd,
        }
