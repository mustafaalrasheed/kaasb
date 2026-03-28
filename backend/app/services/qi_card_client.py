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
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import ClassVar

import httpx

from app.core.config import get_settings
from app.utils.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)

# Exchange rate — update periodically or replace with a live rate API
USD_TO_IQD = 1310.0


def usd_to_iqd(amount_usd: float) -> int:
    """Convert USD to whole IQD, rounded up."""
    raw = amount_usd * USD_TO_IQD
    return int(raw) + (1 if raw % 1 > 0 else 0)


class QiCardError(Exception):
    """Raised when the Qi Card API returns an error or network failure."""
    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class QiCardClient:
    """
    Async HTTP client for the Qi Card payment gateway (v0 API).

    Usage:
        client = QiCardClient()
        result = await client.create_payment(
            amount_usd=150.0,
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
    # Create Payment
    # =========================================================================

    @async_retry(max_attempts=3, base_delay=1.0, exceptions=(httpx.RequestError,))
    async def create_payment(
        self,
        amount_usd: float,
        order_id: str,
        success_url: str,
        failure_url: str,
        cancel_url: str,
        currency: str = "IQD",
    ) -> dict:
        """
        Initiate a Qi Card payment.

        Returns:
            {
                "link":       "https://pay.qi.iq/...",  # redirect user here
                "order_id":   "escrow-<uuid>",
                "amount_iqd": 196500,
                "amount_usd": 150.0,
            }
        """
        amount_iqd = usd_to_iqd(amount_usd)

        if not self._is_configured():
            return self._mock_create(amount_usd, amount_iqd, order_id)

        payload = {
            "order": {
                "amount": amount_iqd,
                "currency": currency,
                "orderId": order_id,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "successUrl": success_url,
            "failureUrl": failure_url,
            "cancelUrl": cancel_url,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await self._circuit.call(
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
                response.status_code, response.text,
            )
            raise QiCardError(
                "Qi Card rejected payment creation",
                status_code=response.status_code,
                response_body=response.text,
            )

        body = response.json()

        if not body.get("success"):
            logger.error("Qi Card create_payment returned success=false: %s", body)
            raise QiCardError(
                f"Qi Card payment creation failed: {body}",
                status_code=response.status_code,
                response_body=response.text,
            )

        link = body.get("data", {}).get("link")
        if not link:
            raise QiCardError(
                f"Qi Card response missing data.link: {body}",
                response_body=response.text,
            )

        logger.info(
            "Qi Card payment created: order_id=%s amount_iqd=%d",
            order_id, amount_iqd,
        )

        return {
            "link": link,
            "order_id": order_id,
            "amount_iqd": amount_iqd,
            "amount_usd": amount_usd,
        }

    # =========================================================================
    # Mock helpers (used when QI_CARD_API_KEY is not set)
    # =========================================================================

    def _mock_create(self, amount_usd: float, amount_iqd: int, order_id: str) -> dict:
        mock_id = uuid.uuid4().hex[:12]
        logger.info(
            "[MOCK] Qi Card create_payment: order_id=%s amount_usd=%.2f amount_iqd=%d",
            order_id, amount_usd, amount_iqd,
        )
        return {
            "link": f"https://merchant.uat.pay.qi.iq/mock-pay/{mock_id}?orderId={order_id}",
            "order_id": order_id,
            "amount_iqd": amount_iqd,
            "amount_usd": amount_usd,
        }
