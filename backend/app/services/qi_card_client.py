"""
Kaasb Platform - Qi Card Payment Gateway Client

UAT endpoint : https://api.uat.pay.qi.iq/api/v1
Production   : https://api.pay.qi.iq/api/v1
Docs         : https://docs.pay-uat.qi.iq/

Authentication (every request):
  Authorization: Basic base64(QI_CARD_MERCHANT_ID:QI_CARD_SECRET_KEY)
  X-Api-Key:     QI_CARD_API_KEY
  Content-Type:  application/json

Payment flow:
  1. POST /payment            → returns formUrl (redirect user here)
  2. User completes payment on Qi Card
  3. Qi Card POSTs to notificationUrl (webhook) AND redirects browser to finishPaymentUrl
  4. GET  /payment/{id}/status → verify status is SUCCESS before confirming

Currency: IQD (Iraqi Dinar). Amount in whole dinars (e.g. 50000 = 50,000 IQD).
USD→IQD conversion: 1 USD ≈ 1,310 IQD (update USD_TO_IQD as needed).
"""

import base64
import logging
import uuid
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
    """Raised when the Qi Card API returns an error response."""
    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


# Qi Card payment status values (from API)
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_AUTH_FAILED = "AUTHENTICATION_FAILED"
STATUS_CREATED = "CREATED"
STATUS_FORM_SHOWED = "FORM_SHOWED"

TERMINAL_STATUSES = {STATUS_SUCCESS, STATUS_FAILED, STATUS_AUTH_FAILED}


class QiCardClient:
    """
    Async HTTP client for the Qi Card payment gateway (v1 API).

    Usage:
        client = QiCardClient()

        # Initiate payment — redirect user to result["form_url"]
        result = await client.create_payment(
            amount_usd=150.0,
            order_id="escrow-<uuid>",
            notification_url="https://kaasb.com/api/v1/payments/qi-card/webhook",
            finish_url="https://kaasb.com/payment/result",
            description="Milestone: Design mockups",
            customer_first_name="Ahmed",
            customer_last_name="Al-Rasheed",
            customer_email="ahmed@example.com",
            customer_phone="9647801234567",
        )
        redirect_to(result["form_url"])

        # Verify payment status (always call this before confirming in your DB)
        status = await client.get_payment_status(result["payment_id"])
        if status["status"] == "SUCCESS":
            ...
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

    def _headers(self) -> dict:
        """Build required auth headers for every Qi Card API request."""
        creds = base64.b64encode(
            f"{self.settings.QI_CARD_MERCHANT_ID}:{self.settings.QI_CARD_SECRET_KEY}".encode()
        ).decode()
        headers = {
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.settings.QI_CARD_API_KEY:
            headers["X-Api-Key"] = self.settings.QI_CARD_API_KEY
        return headers

    def _is_configured(self) -> bool:
        """True when real merchant credentials are present."""
        return bool(
            self.settings.QI_CARD_MERCHANT_ID
            and self.settings.QI_CARD_SECRET_KEY
            and self.settings.QI_CARD_API_KEY
        )

    def _check_error(self, data: dict, context: str) -> None:
        """Raise QiCardError if the response body contains an error field."""
        if "error" in data:
            err = data["error"]
            code = err.get("code", 0)
            msg = err.get("message", "Unknown error")
            raise QiCardError(f"Qi Card {context} error [{code}]: {msg}")

    # =========================================================================
    # Create Payment
    # =========================================================================

    @async_retry(max_attempts=3, base_delay=1.0, exceptions=(httpx.RequestError,))
    async def create_payment(
        self,
        amount_usd: float,
        order_id: str,
        notification_url: str,
        finish_url: str,
        description: str = "",
        customer_first_name: str = "",
        customer_last_name: str = "",
        customer_email: str = "",
        customer_phone: str = "",
    ) -> dict:
        """
        Initiate a Qi Card payment.

        Returns:
            {
                "payment_id":  "pi_xxxxxxxxxxxx",   # Qi Card's payment ID
                "form_url":    "https://pay.qi.iq/form?token=xxx",  # redirect user here
                "request_id":  "<uuid>",
                "amount_iqd":  65500,
                "amount_usd":  50.0,
                "status":      "CREATED",
            }
        """
        amount_iqd = usd_to_iqd(amount_usd)
        request_id = str(uuid.uuid4())

        if not self._is_configured():
            return self._mock_create(amount_usd, amount_iqd, order_id, request_id)

        payload: dict = {
            "requestId": request_id,
            "amount": amount_iqd,
            "currency": "IQD",
            "locale": "ar_IQ",
            "finishPaymentUrl": finish_url,
            "notificationUrl": notification_url,
            "additionalInfo": {"order_id": order_id},
            "description": description[:255],
        }

        # Include customer info if available (improves 3DS success rate)
        customer: dict = {}
        if customer_first_name:
            customer["firstName"] = customer_first_name
        if customer_last_name:
            customer["lastName"] = customer_last_name
        if customer_email:
            customer["email"] = customer_email
        if customer_phone:
            # Qi Card expects international format: 9647XXXXXXXXX
            customer["phone"] = customer_phone
        if customer:
            payload["customerInfo"] = customer

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await self._circuit.call(
                    http.post,
                    f"{self.base_url}/payment",
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

        data = response.json()
        self._check_error(data, "create_payment")

        logger.info(
            "Qi Card payment created: payment_id=%s order_id=%s amount=%s IQD",
            data.get("paymentId"), order_id, amount_iqd,
        )

        return {
            "payment_id": data["paymentId"],
            "form_url": data["formUrl"],
            "request_id": data.get("requestId", request_id),
            "amount_iqd": amount_iqd,
            "amount_usd": amount_usd,
            "status": data.get("status", STATUS_CREATED),
        }

    # =========================================================================
    # Get Payment Status
    # =========================================================================

    @async_retry(max_attempts=3, base_delay=1.0, exceptions=(httpx.RequestError,))
    async def get_payment_status(self, payment_id: str) -> dict:
        """
        Fetch the current status of a payment from Qi Card.
        Always call this to verify before updating your database.

        Returns:
            {
                "payment_id":  "pi_xxx",
                "status":      "SUCCESS" | "FAILED" | "AUTHENTICATION_FAILED" | "CREATED" | "FORM_SHOWED",
                "amount_iqd":  65500,
                "confirmed_amount": 65500 | None,
                "canceled":    False,
                "raw":         { ...full Qi Card response... },
            }
        """
        if not self._is_configured():
            # In mock mode, always return success
            return {
                "payment_id": payment_id,
                "status": STATUS_SUCCESS,
                "amount_iqd": 0,
                "confirmed_amount": None,
                "canceled": False,
                "raw": {},
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await self._circuit.call(
                    http.get,
                    f"{self.base_url}/payment/{payment_id}/status",
                    headers=self._headers(),
                )
        except CircuitOpenError as e:
            raise QiCardError(f"Payment gateway unavailable: {e}") from e
        except httpx.RequestError as e:
            raise QiCardError(f"Network error: {e}") from e

        if response.status_code != 200:
            raise QiCardError(
                f"Failed to fetch payment status for {payment_id}",
                status_code=response.status_code,
                response_body=response.text,
            )

        data = response.json()
        self._check_error(data, "get_payment_status")

        return {
            "payment_id": payment_id,
            "status": data.get("status", "UNKNOWN"),
            "amount_iqd": data.get("amount", 0),
            "confirmed_amount": data.get("confirmedAmount"),
            "canceled": data.get("canceled", False),
            "raw": data,
        }

    # =========================================================================
    # Cancel Payment
    # =========================================================================

    @async_retry(max_attempts=2, base_delay=1.0, exceptions=(httpx.RequestError,))
    async def cancel_payment(self, payment_id: str, amount_iqd: int) -> bool:
        """
        Cancel a pending payment.
        Only works while payment is in CREATED or FORM_SHOWED status.
        Returns True on success.
        """
        if not self._is_configured():
            logger.info("[MOCK] Qi Card cancel_payment: %s", payment_id)
            return True

        payload = {
            "requestId": str(uuid.uuid4()),
            "amount": amount_iqd,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await self._circuit.call(
                    http.post,
                    f"{self.base_url}/payment/{payment_id}/cancel",
                    json=payload,
                    headers=self._headers(),
                )
        except (CircuitOpenError, httpx.RequestError) as e:
            logger.error("Qi Card cancel_payment error: %s", e)
            return False

        if response.status_code not in (200, 201):
            logger.warning(
                "Qi Card cancel_payment failed: payment_id=%s status=%s body=%s",
                payment_id, response.status_code, response.text,
            )
            return False

        data = response.json()
        return data.get("canceled", False)

    # =========================================================================
    # Refund Payment
    # =========================================================================

    @async_retry(max_attempts=3, base_delay=1.0, exceptions=(httpx.RequestError,))
    async def refund_payment(self, payment_id: str, amount_iqd: int, reason: str = "") -> dict:
        """
        Issue a full or partial refund for a completed payment.
        Partial refunds are supported — pass any amount ≤ original.

        Returns:
            {"refund_id": "...", "status": "SUCCESS", "amount_iqd": ...}
        """
        if not self._is_configured():
            logger.info("[MOCK] Qi Card refund_payment: %s %d IQD", payment_id, amount_iqd)
            return {
                "refund_id": f"ref_mock_{uuid.uuid4().hex[:10]}",
                "status": STATUS_SUCCESS,
                "amount_iqd": amount_iqd,
            }

        payload = {
            "requestId": str(uuid.uuid4()),
            "amount": amount_iqd,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                response = await self._circuit.call(
                    http.post,
                    f"{self.base_url}/payment/{payment_id}/refund",
                    json=payload,
                    headers=self._headers(),
                )
        except CircuitOpenError as e:
            raise QiCardError(f"Payment gateway unavailable: {e}") from e
        except httpx.RequestError as e:
            raise QiCardError(f"Network error: {e}") from e

        if response.status_code not in (200, 201):
            raise QiCardError(
                f"Qi Card refund failed for {payment_id}",
                status_code=response.status_code,
                response_body=response.text,
            )

        data = response.json()
        self._check_error(data, "refund_payment")

        return {
            "refund_id": data.get("refundId") or data.get("requestId"),
            "status": data.get("status", STATUS_SUCCESS),
            "amount_iqd": amount_iqd,
        }

    # =========================================================================
    # Mock helpers (used when credentials not configured)
    # =========================================================================

    def _mock_create(
        self, amount_usd: float, amount_iqd: int, order_id: str, request_id: str
    ) -> dict:
        payment_id = f"pi_mock_{uuid.uuid4().hex[:12]}"
        logger.info(
            "[MOCK] Qi Card create_payment: order_id=%s amount_usd=%.2f amount_iqd=%d",
            order_id, amount_usd, amount_iqd,
        )
        return {
            "payment_id": payment_id,
            "form_url": f"https://merchant.uat.pay.qi.iq/mock-pay/{payment_id}",
            "request_id": request_id,
            "amount_iqd": amount_iqd,
            "amount_usd": amount_usd,
            "status": STATUS_CREATED,
        }
