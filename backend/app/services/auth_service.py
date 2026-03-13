"""
Kaasb Platform - Authentication Service
Business logic for user registration, login, and token management.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User, UserRole, UserStatus
from app.models.refresh_token import RefreshToken
from app.schemas.user import UserRegister, UserLogin, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.config import get_settings
from app.utils.sanitize import sanitize_text, sanitize_username

logger = logging.getLogger(__name__)
settings = get_settings()

# Used to ensure login takes constant time even when user is not found
DUMMY_HASH = "$2b$12$dummyhashtopreventtimingattackxxxxxxxxxxxxxxxxxxx"


class AuthService:
    """Authentication service for user management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _hash_token(token: str) -> str:
        """SHA-256 hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def register(self, data: UserRegister) -> User:
        """Register a new user."""
        # Sanitize input before duplicate checks
        data.username = sanitize_username(data.username)
        data.first_name = sanitize_text(data.first_name)
        data.last_name = sanitize_text(data.last_name)

        # Check if email already exists
        existing = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration failed. An account with this email or username may already exist.",
            )

        # Check if username already exists
        existing = await self.db.execute(
            select(User).where(User.username == data.username)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Registration failed. An account with this email or username may already exist.",
            )

        # Create new user
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            primary_role=UserRole(data.primary_role),
            status=UserStatus.ACTIVE,  # Skip email verification for MVP
            is_email_verified=True,  # Auto-verify for MVP
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        logger.info(f"User registered: {user.id} ({user.primary_role})")
        return user

    async def login(self, data: UserLogin) -> TokenResponse:
        """Authenticate user and return JWT tokens."""
        # Find user by email
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()

        # Timing-safe: always run bcrypt even when user not found
        if not user:
            verify_password(data.password, DUMMY_HASH)
            logger.warning(f"Failed login attempt for unknown email: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            logger.warning(f"Login attempt on locked account: user={user.id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked. Try again later.",
            )

        if not verify_password(data.password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 10:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                logger.warning(f"Account locked due to failed attempts: user={user.id}")
            await self.db.flush()
            logger.warning(f"Failed login attempt for email: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if user.status == UserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended",
            )

        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        user.is_online = True
        await self.db.flush()

        # Generate tokens
        token_data = {"sub": str(user.id), "role": user.primary_role.value}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Store refresh token hash for revocation support
        expires = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        rt = RefreshToken(
            token_hash=self._hash_token(refresh_token),
            user_id=user.id,
            expires_at=expires,
        )
        self.db.add(rt)
        await self.db.flush()

        logger.info(f"Login successful: user={user.id}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def get_current_user(self, token: str) -> User:
        """Get the current authenticated user from JWT token."""
        payload = decode_token(token)

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active",
            )

        return user

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Generate new token pair from a valid refresh token."""
        # Check refresh token against DB before decoding
        token_hash = self._hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        stored_token = result.scalar_one_or_none()
        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type - expected refresh token",
            )

        user_id = payload.get("sub")
        result = await self.db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Revoke old token
        stored_token.revoked = True

        # Generate new token pair
        token_data = {"sub": str(user.id), "role": user.primary_role.value}
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        # Store new refresh token
        expires = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        new_rt = RefreshToken(
            token_hash=self._hash_token(new_refresh_token),
            user_id=user.id,
            expires_at=expires,
        )
        self.db.add(new_rt)
        await self.db.flush()

        logger.info(f"Token refreshed: user={user.id}")

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    async def logout(self, user: User, refresh_token: str) -> None:
        """Revoke the given refresh token."""
        token_hash = self._hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user.id,
            )
        )
        token = result.scalar_one_or_none()
        if token:
            token.revoked = True
            await self.db.flush()
        logger.info(f"User logged out: user={user.id}")

    async def logout_all(self, user: User) -> None:
        """Revoke all refresh tokens for the user."""
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked == False,
            )
            .values(revoked=True)
        )
        await self.db.flush()
        logger.info(f"All sessions terminated: user={user.id}")
