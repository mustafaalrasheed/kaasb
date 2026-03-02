"""
Kaasb Platform - User Schemas
Pydantic models for request validation and response serialization.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


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
    primary_role: str = Field(default="client", pattern=r"^(client|freelancer|admin)$")

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
    """Refresh token request."""

    refresh_token: str


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
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    primary_role: str
    title: Optional[str] = None
    hourly_rate: Optional[float] = None
    skills: Optional[list[str]] = None
    experience_level: Optional[str] = None
    portfolio_url: Optional[str] = None
    avg_rating: float = 0.0
    total_reviews: int = 0
    jobs_completed: int = 0
    is_online: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile."""

    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=2000)
    country: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=200)
    hourly_rate: Optional[float] = Field(None, ge=5.0, le=500.0)
    skills: Optional[list[str]] = Field(None, max_length=20)
    experience_level: Optional[str] = Field(
        None, pattern=r"^(entry|intermediate|expert)$"
    )
    portfolio_url: Optional[str] = Field(None, max_length=500)


class UserMe(UserProfile):
    """Current user response (includes private fields)."""

    email: EmailStr
    is_email_verified: bool
    is_superuser: bool = False
    timezone: Optional[str] = None
    phone: Optional[str] = None
    total_earnings: float = 0.0
    total_spent: float = 0.0
    last_login: Optional[datetime] = None


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


# === Paginated Responses ===


class UserListResponse(BaseModel):
    """Paginated list of user profiles."""

    users: list[UserProfile]
    total: int
    page: int
    page_size: int
    total_pages: int
