"""
Kaasb Platform - User Model
Supports both freelancers and clients with role-based fields.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class UserRole(str, enum.Enum):
    """User roles on the platform."""
    CLIENT = "client"
    FREELANCER = "freelancer"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    """Account status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    PENDING_VERIFICATION = "pending_verification"


class User(BaseModel):
    """
    User model - represents both freelancers and clients.
    A user can have both roles simultaneously.
    """

    __tablename__ = "users"

    # === Authentication ===
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # === Social Login IDs (prevent duplicate accounts across providers) ===
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    facebook_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    # === Profile ===
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # === Role & Status ===
    primary_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.CLIENT, nullable=False, index=True
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.PENDING_VERIFICATION, nullable=False, index=True
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    # === Freelancer-Specific Fields ===
    title: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )  # e.g., "Senior Python Developer"
    hourly_rate: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    skills: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )  # ["Python", "FastAPI", "React"]
    experience_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # entry, intermediate, expert
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # === Stats (denormalized for performance) ===
    total_earnings: Mapped[float] = mapped_column(Numeric(12, 4), default=0.0)
    total_spent: Mapped[float] = mapped_column(Numeric(12, 4), default=0.0)
    jobs_completed: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)

    # === Soft delete ===
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # === Activity ===
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Updated when the user's last WebSocket disconnects — powers "Last seen"
    # fallback UI. Live "online now" state is held in Redis (see presence service).
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)

    # === Login attempt tracking ===
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # === Token invalidation ===
    # Incremented on logout-all to invalidate all outstanding access tokens
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False, server_default="0")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.primary_role.value})>"
