"""
Kaasb Platform - Application Configuration
All settings are loaded from environment variables with sensible defaults.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # === App ===
    APP_NAME: str = "Kaasb"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # === Database ===
    DATABASE_URL: str = "postgresql+asyncpg://kaasb_user:kaasb_secret_2024@localhost:5432/kaasb_db"

    # Sync URL for Alembic migrations
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "")

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === Auth / JWT ===
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
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

    # === Email (for future use) ===
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - call this throughout the app."""
    return Settings()
