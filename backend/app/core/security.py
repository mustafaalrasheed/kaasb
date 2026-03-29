"""
Kaasb Platform - Security Utilities
Password hashing with bcrypt and JWT token management.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from functools import partial

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction (auto_error=False to allow cookie fallback)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/login",
    auto_error=False,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password (sync — use hash_password_async in async contexts)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (sync — use verify_password_async in async contexts)."""
    return pwd_context.verify(plain_password, hashed_password)


async def hash_password_async(password: str) -> str:
    """Hash password in thread pool — bcrypt is CPU-bound (~200ms) and blocks the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(pwd_context.hash, password))


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Verify password in thread pool — prevents blocking the event loop during login."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(pwd_context.verify, plain_password, hashed_password))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Alias used by auth_service and other callers
get_password_hash = hash_password


def create_email_token(user_id: str, token_type: str, expires_minutes: int) -> str:
    """Create a signed JWT token for email verification or password reset."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "jti": str(uuid.uuid4()),  # Unique ID for single-use enforcement
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_email_token(token: str, expected_type: str) -> dict:
    """Decode and validate an email token. Returns payload or raises ValueError."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            raise ValueError("Invalid token type")
        return payload
    except JWTError as exc:
        raise ValueError(f"Invalid or expired token: {exc}") from exc
