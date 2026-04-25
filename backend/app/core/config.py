"""
Kaasb Platform - Application Configuration
All settings are loaded from environment variables with sensible defaults.
"""

import logging
import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # === App ===
    APP_NAME: str = "Kaasb"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # === Database ===
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/kaasb_db"

    # Sync URL for Alembic migrations
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === Auth / JWT ===
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # === CORS ===
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # === File Uploads ===
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    UPLOAD_DIR: str = "uploads"

    # === Platform Settings ===
    PLATFORM_FEE_PERCENT: float = 10.0  # 10% platform fee

    # Stamped onto ``users.terms_version`` when a user accepts the legal
    # checkbox at signup. Bump this (and the /terms + /privacy page copy)
    # together whenever the legal text materially changes; existing
    # accounts will be forced to re-accept on next login.
    TERMS_VERSION: str = "2026-04-25"

    # === Dual-Control on Payouts ===
    # Escrow releases above this IQD amount require a SECOND admin to approve
    # before the money actually moves. Releases at/below this amount go through
    # on a single admin click. Set to 0 to disable the threshold (every release
    # requires second approval). Set very high to effectively disable dual-control.
    PAYOUT_APPROVAL_THRESHOLD_IQD: float = 500_000.0

    # Minimum freelancer-initiated payout withdrawal, in IQD. Prevents tiny
    # withdrawals (e.g. 100 IQD) that cost more in admin processing time than
    # the payout is worth.
    MINIMUM_PAYOUT_IQD: float = 50_000.0

    # === Qi Card (Iraqi Payment Gateway) ===
    # === QiCard v0 (legacy, being decommissioned) ===
    # As of 2026-04-25 the production v0 host (api.pay.qi.iq) returns NXDOMAIN
    # and live payments are broken. Phase 4 migrates to the v1 3DS API below;
    # v0 settings are kept for rollback and for any merchant who hasn't been
    # cut over yet. QI_CARD_API_KEY → Authorization header (raw key, no prefix).
    QI_CARD_API_KEY: str = ""
    QI_CARD_BASE_URL: str = "https://api.pay.qi.iq/api/v0/transactions/business/token"
    QI_CARD_SANDBOX_URL: str = "https://api.uat.pay.qi.iq/api/v0/transactions/business/token"
    QI_CARD_SANDBOX: bool = True  # Set to False in production
    QI_CARD_CURRENCY: str = "IQD"  # Iraqi Dinar

    # === QiCard v1 3DS (Phase 4) ===
    # The current live merchant API. Different host, different auth model.
    # All four operations live under the same base host:
    #   POST   /api/v1/payment                     create
    #   GET    /api/v1/payment/{paymentId}/status  verify
    #   POST   /api/v1/payment/{paymentId}/cancel  cancel
    #   POST   /api/v1/payment/{paymentId}/refund  refund (full + partial)
    # Auth is HTTP Basic (user/pass) + an X-Terminal-Id header. RSA-signed
    # X-Signature is also accepted; we'll start with Basic for simplicity.
    # Once these are populated AND ``QI_CARD_USE_V1`` is true, the client
    # routes through the v1 path. Keep them empty in dev/CI so the mock
    # path keeps working without secrets.
    QI_CARD_V1_HOST: str = "https://3ds-api.qi.iq"
    QI_CARD_V1_SANDBOX_HOST: str = "https://uat-sandbox-3ds-api.qi.iq"
    QI_CARD_V1_USER: str = ""
    QI_CARD_V1_PASS: str = ""
    QI_CARD_V1_TERMINAL_ID: str = ""
    # Feature flag: only flip to true once the four env vars above are set
    # AND a successful UAT smoke test has been recorded.
    QI_CARD_USE_V1: bool = False

    # === Zain Cash (parallel gateway) ===
    # Iraqi mobile-money product from Zain. Real merchant API (unlike
    # Asiacell airtime), JWT-signed init flow:
    #   1. POST /transaction/init with a JWT signed by ZAIN_CASH_MERCHANT_SECRET,
    #      claims include {amount, serviceType, msisdn, orderId, redirectUrl,
    #      iat, exp}. Body = {token: <jwt>, merchantId, lang}.
    #   2. Response carries {id} — the operation id.
    #   3. Redirect buyer to /transaction/pay?id=<operation_id>.
    #   4. After buyer pays / cancels, ZC redirects browser to
    #      ZAIN_CASH_REDIRECT_URL?token=<JWT> where the JWT carries
    #      {orderId, status: 'success'|'failed', operationId, ...}.
    #
    # Hosts:
    #   sandbox   https://test.zaincash.iq
    #   prod      https://api.zaincash.iq
    # Auth: HS256 JWT signed with the merchant secret (no separate API key).
    ZAIN_CASH_PRODUCTION: bool = False
    ZAIN_CASH_SANDBOX_URL: str = "https://test.zaincash.iq"
    ZAIN_CASH_PRODUCTION_URL: str = "https://api.zaincash.iq"
    ZAIN_CASH_MERCHANT_ID: str = ""
    ZAIN_CASH_MERCHANT_SECRET: str = ""
    ZAIN_CASH_MSISDN: str = ""  # Merchant phone, e.g. 9647827124591
    ZAIN_CASH_LANG: str = "ar"  # ar | en — passed to ZC for the hosted page
    ZAIN_CASH_SERVICE_TYPE: str = "Kaasb"  # Free-form label shown on ZC's pay page
    # Idempotency window for create_payment — within this many seconds a repeat
    # call with the same order_id returns the cached redirect link instead of
    # creating a new Qi Card charge. Matches Qi Card's own payment-session TTL.
    QI_CARD_IDEMPOTENCY_TTL_SEC: int = 900  # 15 minutes

    # === Domain ===
    DOMAIN: str = "localhost"

    # === Email (Resend) ===
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "Kaasb <noreply@kaasb.com>"
    EMAIL_FROM_NAME: str = "Kaasb"
    FRONTEND_URL: str = "http://localhost:3000"

    # === Monitoring & Observability ===
    # Sentry DSN — leave empty to disable error tracking (safe default)
    SENTRY_DSN: str = ""
    # Slow request threshold for warning log (milliseconds)
    SLOW_REQUEST_THRESHOLD_MS: int = 1000
    # Log level override (DEBUG | INFO | WARNING | ERROR)
    LOG_LEVEL: str = "INFO"
    # Bearer token for /health/detailed endpoint — leave empty to disable endpoint
    HEALTH_BEARER_TOKEN: str = ""

    # === Social Login ===
    GOOGLE_CLIENT_ID: str = ""   # Google OAuth Client ID (from Google Cloud Console)
    FACEBOOK_APP_ID: str = ""    # Facebook App ID (from Meta for Developers)
    FACEBOOK_APP_SECRET: str = ""  # Facebook App Secret (for token verification)

    # === Twilio (SMS + WhatsApp OTP — production) ===
    # Leave all empty to fall back to email-based OTP delivery (beta mode).
    # Priority: WhatsApp (if TWILIO_WHATSAPP_NUMBER set) → SMS (if TWILIO_PHONE_NUMBER set) → email.
    TWILIO_ACCOUNT_SID: str = ""        # From https://console.twilio.com
    TWILIO_AUTH_TOKEN: str = ""         # From https://console.twilio.com
    TWILIO_PHONE_NUMBER: str = ""       # Twilio SMS number, e.g. +1XXXXXXXXXX
    TWILIO_WHATSAPP_NUMBER: str = ""    # Twilio WhatsApp sender, e.g. whatsapp:+14155238886

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        """Ensure critical secrets are set in production and generate safe defaults in dev."""
        if not self.SECRET_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError(
                    "SECRET_KEY must be set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            self.SECRET_KEY = secrets.token_hex(32)
            logger.warning("SECRET_KEY not set — generated a random key (not persisted across restarts)")

        if self.DEBUG and self.ENVIRONMENT == "production":
            raise ValueError("DEBUG must be False in production")

        if self.ENVIRONMENT == "production":
            if not self.QI_CARD_API_KEY and not self.QI_CARD_SANDBOX and not self.QI_CARD_USE_V1:
                raise ValueError("QI_CARD_API_KEY must be set when QI_CARD_SANDBOX is False")
            # If the v1 path is enabled in production, all four credential
            # slots must be populated. Catching this at boot beats discovering
            # a half-configured client when a customer tries to pay.
            if self.QI_CARD_USE_V1:
                missing = [
                    name for name, val in (
                        ("QI_CARD_V1_HOST", self.QI_CARD_V1_HOST),
                        ("QI_CARD_V1_USER", self.QI_CARD_V1_USER),
                        ("QI_CARD_V1_PASS", self.QI_CARD_V1_PASS),
                        ("QI_CARD_V1_TERMINAL_ID", self.QI_CARD_V1_TERMINAL_ID),
                    )
                    if not val
                ]
                if missing:
                    raise ValueError(
                        "QI_CARD_USE_V1 is true but required v1 settings are "
                        f"missing: {', '.join(missing)}"
                    )
            # Zain Cash: same fail-fast pattern. If the merchant credentials
            # are partially set (e.g. someone added two of three), the
            # client would silently 401 every payment attempt.
            zc_set = [
                bool(self.ZAIN_CASH_MERCHANT_ID),
                bool(self.ZAIN_CASH_MERCHANT_SECRET),
                bool(self.ZAIN_CASH_MSISDN),
            ]
            if any(zc_set) and not all(zc_set):
                raise ValueError(
                    "Zain Cash configuration is partial — set all of "
                    "ZAIN_CASH_MERCHANT_ID, ZAIN_CASH_MERCHANT_SECRET, "
                    "and ZAIN_CASH_MSISDN, or none of them."
                )
            if not self.RESEND_API_KEY:
                logger.warning("RESEND_API_KEY not set — transactional emails will not be sent")
            # In production: replace dev origins with production-only origins.
            # Previously this only appended, leaving localhost:3000 in the CORS allowlist,
            # which lets any local process send credentialed requests to the prod API.
            if self.DOMAIN and self.DOMAIN != "localhost":
                self.CORS_ORIGINS = [
                    f"https://{self.DOMAIN}",
                    f"https://www.{self.DOMAIN}",
                ]

        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - call this throughout the app."""
    return Settings()
