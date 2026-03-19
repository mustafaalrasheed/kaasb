"""
Kaasb Platform - Qi Card Payment Gateway Client
Iraqi payment gateway integration for escrow funding and freelancer payouts.

API Overview (based on qi.iq developer documentation):
  POST /create-payment       - Initiate a payment, returns redirect URL
  GET  /get-payment-status   - Poll payment status by payment_id
  POST /cancel-payment       - Cancel a pending payment
  POST /refund-payment       - Refund a completed payment

Authentication:
  - Basic Auth: base64(merchant_id:secret_key)
  - Optional HMAC-SHA256 signature on the request body

Currency: IQD (Iraqi Dinar). 1 USD ≈ 1,310 IQD (update rate as needed).

To go live:
  1. Contact Qi Card / International Smart Card: https://qi.iq
  2. Get merchant_id, secret_key, and sandbox credentials
  3. Set QI_CARD_SANDBOX=false, QI_CARD_MERCHANT_ID, QI_CARD_SECRET_KEY in .env
"""

import base64
import hashlib
import hmac
import logging
import uuid

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Exchange rate placeholder — replace with live rate API in production
USD_TO_IQD = 1310.0


def usd_to_iqd(amount_usd: float) -> int:
    """Convert USD amount to IQD (whole dinars, rounded up)."""
    return int(amount_usd * USD_TO_IQD) + (1 if (amount_usd * USD_TO_IQD) % 1 > 0 else 0)


class QiCardError(Exception):
    """Raised when Qi Card API returns an error."""
    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class QiCardClient:
    """
    Async HTTP client for the Qi Card payment gateway.

    Usage:
        client = QiCardClient()
        payment = await client.create_payment(
            amount_usd=150.0,
            order_id="escrow-<uuid>",
            callback_url="https://kaasb.com/api/v1/payments/qi-card/webhook",
            return_url="https://kaasb.com/payment/result",
            description="Milestone: Design mockups",
        )
        # Redirect client to payment["redirect_url"]
    """

    def __init__(self):
        self.settings = get_settings()
        self.base_url = (
            self.settings.QI_CARD_SANDBOX_URL
            if self.settings.QI_CARD_SANDBOX
            else self.settings.QI_CARD_BASE_URL
        )
        self._auth_header = self._build_auth_header()

    def _build_auth_header(self) -> str:
        """Build HTTP Basic Auth header from merchant credentials."""
        credentials = f"{self.settings.QI_CARD_MERCHANT_ID}:{self.settings.QI_CARD_SECRET_KEY}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _sign_payload(self, payload: dict) -> str:
        """
        Generate HMAC-SHA256 signature for a request payload.
        Sorted key=value pairs joined with & then signed with secret_key.
        """
        message = "&".join(f"{k}={v}" for k, v in sorted(payload.items()))
        return hmac.new(
            self.settings.QI_CARD_SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """
        Verify that an incoming webhook came from Qi Card.
        Qi Card sends an X-QiCard-Signature header with the HMAC.
        """
        if not self.settings.QI_CARD_SECRET_KEY:
            if self.settings.QI_CARD_SANDBOX:
                logger.warning("QI_CARD_SECRET_KEY not set in sandbox — skipping signature verification")
                return True
            logger.error("QI_CARD_SECRET_KEY not set in non-sandbox mode — rejecting webhook")
            return False

        expected = hmac.new(
            self.settings.QI_CARD_SECRET_KEY.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _is_configured(self) -> bool:
        """True if real credentials are set (not sandbox placeholder)."""
        return bool(self.settings.QI_CARD_MERCHANT_ID and self.settings.QI_CARD_SECRET_KEY)

    # =========================================================================
    # Payment Operations
    # =========================================================================

    async def create_payment(
        self,
        amount_usd: float,
        order_id: str,
        callback_url: str,
        return_url: str,
        description: str = "",
    ) -> dict:
        """
        Initiate a Qi Card payment.

        Returns:
            {
                "payment_id": "qc_xxxxxxxx",
                "redirect_url": "https://pay.qi.iq/...",
                "amount_iqd": 196500,
                "amount_usd": 150.0,
                "status": "pending",
            }
        """
        amount_iqd = usd_to_iqd(amount_usd)

        if not self._is_configured():
            return self._mock_create_payment(amount_usd, amount_iqd, order_id)

        payload = {
            "merchant_id": self.settings.QI_CARD_MERCHANT_ID,
            "order_id": order_id,
            "amount": amount_iqd,
            "currency": "IQD",
            "description": description[:255],
            "callback_url": callback_url,
            "return_url": return_url,
        }
        payload["signature"] = self._sign_payload(payload)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/create-payment",
                    json=payload,
                    headers={
                        "Authorization": self._auth_header,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
        except httpx.RequestError as e:
            logger.error(f"Qi Card network error in create_payment: {e}")
            raise QiCardError(f"Network error connecting to Qi Card: {e}")

        if response.status_code not in (200, 201):
            logger.error(
                f"Qi Card create_payment failed: status={response.status_code} body={response.text}"
            )
            raise QiCardError(
                "Qi Card payment creation failed",
                status_code=response.status_code,
                response_body=response.text,
            )

        data = response.json()
        return {
            "payment_id": data.get("payment_id") or data.get("id"),
            "redirect_url": data.get("redirect_url") or data.get("payment_url"),
            "amount_iqd": amount_iqd,
            "amount_usd": amount_usd,
            "status": data.get("status", "pending"),
        }

    async def get_payment_status(self, payment_id: str) -> dict:
        """
        Poll Qi Card for the current status of a payment.

        Returns:
            {
                "payment_id": "qc_xxxxxxxx",
                "status": "completed" | "pending" | "failed" | "cancelled",
                "amount_iqd": 196500,
            }
        """
        if not self._is_configured():
            return {"payment_id": payment_id, "status": "completed", "amount_iqd": 0}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/get-payment-status",
                    params={"payment_id": payment_id, "merchant_id": self.settings.QI_CARD_MERCHANT_ID},
                    headers={
                        "Authorization": self._auth_header,
                        "Accept": "application/json",
                    },
                )
        except httpx.RequestError as e:
            logger.error(f"Qi Card network error in get_payment_status: {e}")
            raise QiCardError(f"Network error: {e}")

        if response.status_code != 200:
            raise QiCardError(
                "Failed to get payment status",
                status_code=response.status_code,
                response_body=response.text,
            )

        data = response.json()
        return {
            "payment_id": payment_id,
            "status": data.get("status", "unknown"),
            "amount_iqd": data.get("amount", 0),
        }

    async def cancel_payment(self, payment_id: str) -> bool:
        """Cancel a pending payment. Returns True on success."""
        if not self._is_configured():
            logger.info(f"[MOCK] Qi Card cancel_payment: {payment_id}")
            return True

        payload = {
            "merchant_id": self.settings.QI_CARD_MERCHANT_ID,
            "payment_id": payment_id,
        }
        payload["signature"] = self._sign_payload(payload)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/cancel-payment",
                    json=payload,
                    headers={
                        "Authorization": self._auth_header,
                        "Content-Type": "application/json",
                    },
                )
        except httpx.RequestError as e:
            logger.error(f"Qi Card network error in cancel_payment: {e}")
            return False

        return response.status_code in (200, 204)

    async def refund_payment(self, payment_id: str, amount_iqd: int, reason: str = "") -> dict:
        """
        Issue a refund for a completed payment.

        Returns:
            {"refund_id": "...", "status": "refunded", "amount_iqd": ...}
        """
        if not self._is_configured():
            logger.info(f"[MOCK] Qi Card refund_payment: {payment_id} {amount_iqd} IQD")
            return {
                "refund_id": f"qc_refund_mock_{uuid.uuid4().hex[:10]}",
                "status": "refunded",
                "amount_iqd": amount_iqd,
            }

        payload = {
            "merchant_id": self.settings.QI_CARD_MERCHANT_ID,
            "payment_id": payment_id,
            "amount": amount_iqd,
            "reason": reason[:255],
        }
        payload["signature"] = self._sign_payload(payload)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/refund-payment",
                    json=payload,
                    headers={
                        "Authorization": self._auth_header,
                        "Content-Type": "application/json",
                    },
                )
        except httpx.RequestError as e:
            logger.error(f"Qi Card network error in refund_payment: {e}")
            raise QiCardError(f"Network error: {e}")

        if response.status_code not in (200, 201):
            raise QiCardError(
                "Qi Card refund failed",
                status_code=response.status_code,
                response_body=response.text,
            )

        data = response.json()
        return {
            "refund_id": data.get("refund_id") or data.get("id"),
            "status": "refunded",
            "amount_iqd": amount_iqd,
        }

    # =========================================================================
    # Sandbox mock helpers (used when credentials not configured)
    # =========================================================================

    def _mock_create_payment(self, amount_usd: float, amount_iqd: int, order_id: str) -> dict:
        payment_id = f"qc_mock_{uuid.uuid4().hex[:12]}"
        logger.info(
            f"[MOCK] Qi Card create_payment: order_id={order_id} "
            f"amount_usd={amount_usd} amount_iqd={amount_iqd}"
        )
        return {
            "payment_id": payment_id,
            "redirect_url": f"https://sandbox.qi.iq/pay/{payment_id}",
            "amount_iqd": amount_iqd,
            "amount_usd": amount_usd,
            "status": "pending",
        }
