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
    MIN_HOURLY_RATE: float = 5.0
    MAX_HOURLY_RATE: float = 500.0

    # === Stripe ===
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # === Wise (TransferWise) ===
    WISE_API_KEY: str = ""
    WISE_PROFILE_ID: str = ""
    WISE_ENVIRONMENT: str = "sandbox"  # sandbox | production

    # === Qi Card (Iraqi Payment Gateway) ===
    QI_CARD_MERCHANT_ID: str = ""
    QI_CARD_SECRET_KEY: str = ""
    QI_CARD_BASE_URL: str = "https://gateway.qi.iq/api/v1"
    QI_CARD_SANDBOX_URL: str = "https://sandbox.gateway.qi.iq/api/v1"
    QI_CARD_SANDBOX: bool = True  # Set to False in production
    QI_CARD_CURRENCY: str = "IQD"  # Iraqi Dinar

    # === Domain ===
    DOMAIN: str = "localhost"

    # === Email ===
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@kaasb.com"

    # === Monitoring & Observability ===
    # Sentry DSN — leave empty to disable error tracking (safe default)
    SENTRY_DSN: str = ""
    # Slow request threshold for warning log (milliseconds)
    SLOW_REQUEST_THRESHOLD_MS: int = 1000
    # Log level override (DEBUG | INFO | WARNING | ERROR)
    LOG_LEVEL: str = "INFO"

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
            if not self.STRIPE_SECRET_KEY:
                logger.warning("STRIPE_SECRET_KEY not set — Stripe payments will not work")
            if not self.STRIPE_WEBHOOK_SECRET:
                logger.warning("STRIPE_WEBHOOK_SECRET not set — Stripe webhooks will not be verified")
            if not self.QI_CARD_SECRET_KEY and not self.QI_CARD_SANDBOX:
                raise ValueError("QI_CARD_SECRET_KEY must be set when QI_CARD_SANDBOX is False")

        return self


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - call this throughout the app."""
    return Settings()
