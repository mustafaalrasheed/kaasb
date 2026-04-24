"""
Kaasb Platform - User Schemas
Pydantic models for request validation and response serialization.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.utils.phone import normalize_iraqi_phone

# === Auth Schemas ===


class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    username: str = Field(
        min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    primary_role: str = Field(default="client", pattern=r"^(client|freelancer)$")
    # Must be true for the register call to succeed. The front-end already
    # gates the submit button on this, but enforcing server-side means an
    # API client or a tampered request cannot skip it. Persisted as
    # ``users.terms_accepted_at`` + ``users.terms_version`` (signup-audit F1).
    terms_accepted: bool = Field(default=False)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("terms_accepted")
    @classmethod
    def validate_terms_accepted(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "You must accept the Terms of Service, Privacy Policy, "
                "and Acceptable Use Policy to register."
            )
        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Refresh token request.

    refresh_token is optional — the backend prefers the httpOnly cookie.
    Clients that manage tokens manually (API scripts) can pass it in the body.
    """

    refresh_token: str | None = None


class SocialLoginRequest(BaseModel):
    """Request schema for social/OAuth login."""

    provider: str = Field(..., pattern=r"^(google|facebook)$")
    token: str = Field(..., min_length=10, description="Access token from Google or Facebook OAuth flow")
    role: str = Field(default="freelancer", pattern=r"^(client|freelancer)$", description="Role for new accounts")
    # Required for NEW-account creation via social login — the frontend
    # sets this to true only after the user has ticked the legal checkbox.
    # Ignored (and safely None/false) on returning-user logins since they
    # already have ``terms_accepted_at`` stamped from their first registration.
    terms_accepted: bool = Field(default=False)


# === User Profile Schemas ===


class UserBase(BaseModel):
    """Shared user fields."""

    email: EmailStr
    username: str
    first_name: str
    last_name: str
    primary_role: str


class UserProfile(BaseModel):
    """Public user profile response."""

    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    country: str | None = None
    city: str | None = None
    primary_role: str
    title: str | None = None
    skills: list[str] | None = None
    experience_level: str | None = None
    portfolio_url: str | None = None
    avg_rating: float = 0.0
    total_reviews: int = 0
    jobs_completed: int = 0
    is_online: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    display_name: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=2000)
    country: str | None = Field(None, max_length=100)
    city: str | None = Field(None, max_length=100)
    timezone: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=20)
    title: str | None = Field(None, max_length=200)

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str | None) -> str | None:
        return normalize_iraqi_phone(v)
    skills: list[str] | None = Field(None, max_length=20)
    experience_level: str | None = Field(
        None, pattern=r"^(entry|intermediate|expert)$"
    )
    portfolio_url: str | None = Field(None, max_length=500)


class UserMe(UserProfile):
    """Current user response (includes private fields)."""

    email: EmailStr
    is_email_verified: bool
    is_superuser: bool = False
    is_support: bool = False
    timezone: str | None = None
    phone: str | None = None
    total_earnings: float = 0.0
    total_spent: float = 0.0
    last_login: datetime | None = None
    # Chat policy state — the messaging UI reads these to show the
    # suspension banner + countdown and to pre-warn before the next violation.
    chat_violations: int = 0
    chat_suspended_until: datetime | None = None


# === Password Management ===


class PasswordChange(BaseModel):
    """Schema for changing password."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


# === Email / Password Reset Schemas ===


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class PhoneOtpRequest(BaseModel):
    """Request a 6-digit OTP for phone-based login."""

    phone: str = Field(
        ...,
        min_length=7,
        max_length=20,
        pattern=r"^\+?[0-9]{7,19}$",
        description="Phone number in any shape; server normalises to +9647XXXXXXXXX.",
    )

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        return normalize_iraqi_phone(v) or v


class PhoneOtpVerifyRequest(BaseModel):
    """Verify a phone OTP and receive JWT tokens."""

    phone: str = Field(..., min_length=7, max_length=20, pattern=r"^\+?[0-9]{7,19}$")
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^[0-9]{6}$")

    @field_validator("phone")
    @classmethod
    def _normalize_phone(cls, v: str) -> str:
        return normalize_iraqi_phone(v) or v


# === Paginated Responses ===


class UserListResponse(BaseModel):
    """Paginated list of user profiles."""

    users: list[UserProfile]
    total: int
    page: int
    page_size: int
    total_pages: int


# === Session Schemas ===


class SessionOut(BaseModel):
    """Active session metadata for the Settings → Active Sessions UI."""

    id: uuid.UUID
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime
    is_current: bool = False

    model_config = {"from_attributes": True}
