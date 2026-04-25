"""
Kaasb Platform - Zain Cash Payment Gateway Client

Iraqi mobile-money product. Real merchant API (unlike Asiacell airtime),
JWT-signed init flow. Documented sample at:
  https://github.com/hamdongunner/zaincash (the reference Node.js SDK
  Karrar Sattar / Zain shipped with their merchant onboarding email)

Init flow:
  1. Build a JWT signed with the merchant secret (HS256). Claims:
       amount       — IQD whole number, must be >= 250 IQD
       serviceType  — free-form label shown on Zain Cash's hosted page
       msisdn       — merchant phone (settings.ZAIN_CASH_MSISDN)
       orderId      — our internal escrow / order id, echoed back in
                      the redirect token so we can match without
                      trusting query params
       redirectUrl  — where Zain Cash sends the buyer's browser
                      after pay/cancel; ZC appends ?token=<JWT>
       iat / exp    — seconds-since-epoch (the reference SDK uses
                      milliseconds, but Zain accepts seconds and
                      python-jose's verify path is happiest with seconds).
  2. POST {token, merchantId, lang} to /transaction/init.
  3. Response carries {id} — the operation id.
  4. Redirect buyer to {host}/transaction/pay?id={operation_id}.

Redirect handling (separate endpoint, not in this file): on the configured
redirectUrl, ZC appends ?token=<JWT> where the JWT carries
{orderId, status: 'success'|'failed', operationId, ...}. Verify the JWT
with the same merchant secret, then update escrow accordingly.

Currency: IQD (Iraqi Dinar). Minimum 250 IQD per transaction.
"""

import json
import logging
import time
import uuid
from typing import ClassVar

import httpx
from jose import jwt as jose_jwt

from app.core.config import get_settings
from app.utils.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)


# Zain Cash's reference SDK and their published docs reject anything below
# 250 IQD as "amount too small" — surface this client-side so we don't
# round-trip a network call to learn the obvious.
ZAIN_CASH_MIN_AMOUNT_IQD = 250


class ZainCashError(Exception):
    """Raised on Zain Cash API or network failures."""

    def __init__(self, message: str, status_code: int = 0, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ZainCashClient:
    """Async HTTP client for the Zain Cash JWT-signed merchant API.

    Usage:
        client = ZainCashClient()
        result = await client.create_payment(
            amount_iqd=25_000,
            order_id="escrow-<uuid>",
            redirect_url="https://kaasb.com/api/v1/payments/zain-cash/callback",
        )
        # result["redirect_url"] is the hosted-pay URL — send the buyer there.
        # result["operation_id"] is Zain Cash's id for the transaction.
    """

    _circuit: ClassVar[CircuitBreaker | None] = None

    def __init__(self) -> None:
        self.settings = get_settings()
        if ZainCashClient._circuit is None:
            ZainCashClient._circuit = CircuitBreaker(
                name="zain_cash",
                failure_threshold=5,
                recovery_timeout=60.0,
                exceptions=(httpx.RequestError, ZainCashError),
            )

    # ─── URL helpers ────────────────────────────────────────────────────

    @property
    def _base_url(self) -> str:
        return (
            self.settings.ZAIN_CASH_PRODUCTION_URL
            if self.settings.ZAIN_CASH_PRODUCTION
            else self.settings.ZAIN_CASH_SANDBOX_URL
        )

    def _is_configured(self) -> bool:
        s = self.settings
        return all((s.ZAIN_CASH_MERCHANT_ID, s.ZAIN_CASH_MERCHANT_SECRET, s.ZAIN_CASH_MSISDN))

    # ─── Create payment ──────────────────────────────────────────────────

    @async_retry(max_attempts=3, base_delay=1.0, exceptions=(httpx.RequestError,))
    async def create_payment(
        self,
        amount_iqd: int,
        order_id: str,
        redirect_url: str,
    ) -> dict:
        """Init a Zain Cash payment, return the buyer-redirect URL.

        Returns:
            {
                "operation_id": "abc123...",        # Zain Cash's internal id
                "redirect_url": "https://api.zaincash.iq/transaction/pay?id=...",
                "order_id":     "escrow-<uuid>",    # echoed
                "amount_iqd":   25000,              # echoed
            }
        """
        if amount_iqd < ZAIN_CASH_MIN_AMOUNT_IQD:
            raise ZainCashError(
                f"Zain Cash minimum is {ZAIN_CASH_MIN_AMOUNT_IQD} IQD; got {amount_iqd}."
            )

        # Mock path — surfaces in dev / CI when secrets aren't set, so the
        # checkout flow can still be exercised without a real merchant.
        if not self._is_configured():
            return self._mock_create(amount_iqd, order_id)

        now = int(time.time())
        claims = {
            "amount": amount_iqd,
            "serviceType": self.settings.ZAIN_CASH_SERVICE_TYPE,
            "msisdn": self.settings.ZAIN_CASH_MSISDN,
            "orderId": order_id,
            "redirectUrl": redirect_url,
            "iat": now,
            # ZC's reference SDK ships a 4h window. Match it so support
            # tickets that quote "I tried 2 hours ago" still match a
            # signature we'd accept.
            "exp": now + 4 * 60 * 60,
        }
        token = jose_jwt.encode(
            claims,
            self.settings.ZAIN_CASH_MERCHANT_SECRET,
            algorithm="HS256",
        )

        body = {
            "token": token,
            "merchantId": self.settings.ZAIN_CASH_MERCHANT_ID,
            "lang": self.settings.ZAIN_CASH_LANG,
        }

        init_url = f"{self._base_url}/transaction/init"
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await self._circuit.call(  # type: ignore[union-attr]
                    http.post,
                    init_url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
        except CircuitOpenError as exc:
            raise ZainCashError(f"Zain Cash gateway unavailable: {exc}") from exc
        except httpx.RequestError as exc:
            raise ZainCashError(f"Network error reaching Zain Cash: {exc}") from exc

        if response.status_code not in (200, 201):
            logger.error(
                "zain_cash init failed: status=%s body=%s",
                response.status_code, response.text[:300],
            )
            raise ZainCashError(
                "Zain Cash rejected the payment init",
                status_code=response.status_code,
                response_body=response.text,
            )

        try:
            data = response.json()
        except ValueError as exc:
            logger.error("zain_cash init returned non-JSON: %s", response.text[:300])
            raise ZainCashError("Zain Cash returned an invalid response") from exc

        operation_id = data.get("id")
        if not operation_id:
            logger.error(
                "zain_cash init response missing id: %s",
                json.dumps(data)[:300],
            )
            raise ZainCashError(
                "Zain Cash init response missing operation id",
                response_body=response.text,
            )

        pay_url = f"{self._base_url}/transaction/pay?id={operation_id}"
        logger.info(
            "zain_cash payment created: order_id=%s amount_iqd=%d op=%s",
            order_id, amount_iqd, operation_id,
        )
        return {
            "operation_id": operation_id,
            "redirect_url": pay_url,
            "order_id": order_id,
            "amount_iqd": amount_iqd,
        }

    # ─── Verify redirect token ───────────────────────────────────────────

    def verify_redirect_token(self, token: str) -> dict:
        """Verify the JWT Zain Cash appends to the redirect URL.

        Returns the decoded claims dict on success. Caller MUST also
        check ``decoded["status"] == "success"`` before treating the
        transaction as paid — Zain Cash uses the same redirect URL for
        success and failure, distinguishing only via the status claim.

        Raises ``ZainCashError`` if the token is missing, malformed, or
        not signed with our merchant secret. **Never trust the URL's
        query params alone** — only the JWT carries authenticated data.
        """
        if not token:
            raise ZainCashError("Empty Zain Cash redirect token")
        if not self._is_configured():
            # In mock mode, accept a JSON blob masquerading as a token
            # so dev / CI smoke tests can simulate a callback without a
            # real Zain Cash signature. Production never hits this path.
            try:
                return json.loads(token)
            except ValueError as exc:
                raise ZainCashError("Mock-mode redirect token must be JSON") from exc

        try:
            claims = jose_jwt.decode(
                token,
                self.settings.ZAIN_CASH_MERCHANT_SECRET,
                algorithms=["HS256"],
                # Zain Cash sets aud / iss empty in their tokens — disable
                # those checks to keep the verify call from rejecting
                # legitimate callbacks.
                options={"verify_aud": False, "verify_iss": False},
            )
        except Exception as exc:  # jose raises various subclasses
            logger.warning("zain_cash redirect token verify failed: %s", exc)
            raise ZainCashError(f"Zain Cash redirect token rejected: {exc}") from exc
        return claims

    # ─── Mock helpers (dev / CI) ─────────────────────────────────────────

    def _mock_create(self, amount_iqd: int, order_id: str) -> dict:
        mock_id = uuid.uuid4().hex[:12]
        logger.info(
            "[MOCK] zain_cash create_payment: order_id=%s amount_iqd=%d",
            order_id, amount_iqd,
        )
        return {
            "operation_id": mock_id,
            "redirect_url": f"{self._base_url}/mock-pay/{mock_id}?orderId={order_id}",
            "order_id": order_id,
            "amount_iqd": amount_iqd,
        }
