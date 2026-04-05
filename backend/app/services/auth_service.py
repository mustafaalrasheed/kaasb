"""
Kaasb Platform - Authentication Service
Business logic for user registration, login, and token management.
"""

import hashlib
import logging
import random
import secrets as _secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_email_token,
    create_refresh_token,
    decode_token,
    hash_password_async,
    verify_email_token,
    verify_password_async,
)
from app.models.phone_otp import PhoneOtp
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import TokenResponse, UserLogin, UserRegister
from app.services.base import BaseService
from app.utils.sanitize import sanitize_email, sanitize_text, sanitize_username

logger = logging.getLogger(__name__)
settings = get_settings()

# Used to ensure login takes constant time even when user is not found
DUMMY_HASH = "$2b$12$dummyhashtopreventtimingattackxxxxxxxxxxxxxxxxxxx"


def _mask_email(email: str) -> str:
    """Mask email for safe logging: 'user@example.com' -> 'u***@e***.com'."""
    try:
        local, domain = email.rsplit("@", 1)
        domain_parts = domain.rsplit(".", 1)
        masked_local = local[0] + "***" if local else "***"
        masked_domain = domain_parts[0][0] + "***" if domain_parts[0] else "***"
        return f"{masked_local}@{masked_domain}.{domain_parts[1]}" if len(domain_parts) > 1 else f"{masked_local}@{masked_domain}"
    except (ValueError, IndexError):
        return "***"


class AuthService(BaseService):
    """Authentication service for user management."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    @staticmethod
    def _hash_token(token: str) -> str:
        """SHA-256 hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def register(self, data: UserRegister) -> User:
        """Register a new user."""
        # Sanitize input before duplicate checks
        data.email = sanitize_email(data.email)  # type: ignore[assignment]
        data.username = sanitize_username(data.username)  # type: ignore[assignment]
        data.first_name = sanitize_text(data.first_name)  # type: ignore[assignment]
        data.last_name = sanitize_text(data.last_name)  # type: ignore[assignment]

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

        # Create new user — async hash prevents blocking the event loop (~200ms)
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=await hash_password_async(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            primary_role=UserRole(data.primary_role),
            status=UserStatus.ACTIVE,  # Skip email verification for MVP
            is_email_verified=True,  # Auto-verify for MVP
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        logger.info("User registered: %s (%s)", user.id, user.primary_role)
        return user

    async def login(self, data: UserLogin) -> TokenResponse:
        """Authenticate user and return JWT tokens."""
        # Find user by email
        result = await self.db.execute(
            select(User).where(User.email == data.email)
        )
        user = result.scalar_one_or_none()

        # Timing-safe: always run bcrypt even when user not found (async to not block event loop)
        if not user:
            await verify_password_async(data.password, DUMMY_HASH)
            logger.warning("Failed login attempt for unknown email: %s", _mask_email(data.email))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.now(UTC):
            logger.warning("Login attempt on locked account: user=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked. Try again later.",
            )

        if not await verify_password_async(data.password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 10:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=30)
                logger.warning("Account locked due to failed attempts: user=%s", user.id)
            await self.db.flush()
            logger.warning("Failed login attempt for user=%s", user.id)
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
        user.last_login = datetime.now(UTC)
        user.is_online = True
        await self.db.flush()

        # Generate tokens (include token_version so logout-all invalidates access tokens)
        token_data = {"sub": str(user.id), "role": user.primary_role.value, "tv": user.token_version}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Store refresh token hash for revocation support
        expires = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        rt = RefreshToken(
            token_hash=self._hash_token(refresh_token),
            user_id=user.id,
            expires_at=expires,
        )
        self.db.add(rt)
        await self.db.flush()

        logger.info("Login successful: user=%s", user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def social_login(self, provider: str, token: str, role: str = "freelancer", email_service=None) -> TokenResponse:
        """Authenticate via Google or Facebook OAuth token."""
        # Verify token and fetch profile from provider
        if provider == "google":
            email, first_name, last_name, avatar_url = await self._verify_google_token(token)
        elif provider == "facebook":
            email, first_name, last_name, avatar_url = await self._verify_facebook_token(token)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not retrieve email from {provider}. Make sure email permission is granted.",
            )

        # Find existing user by email
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            # Create new user from OAuth profile
            base_username = (first_name + "_" + last_name).lower()
            base_username = "".join(c for c in base_username if c.isalnum() or c == "_")[:20] or "user"

            # Ensure username is unique
            username = base_username
            counter = 1
            while True:
                exists = await self.db.execute(select(User).where(User.username == username))
                if not exists.scalar_one_or_none():
                    break
                username = f"{base_username}{counter}"
                counter += 1

            user = User(
                email=email,
                username=username,
                hashed_password=await hash_password_async(_secrets.token_hex(32)),
                first_name=first_name or "User",
                last_name=last_name or "",
                avatar_url=avatar_url,
                primary_role=UserRole(role),
                status=UserStatus.ACTIVE,
                is_email_verified=True,
            )
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            logger.info("Social login: new user created via %s: %s", provider, user.id)
            if email_service:
                import asyncio
                asyncio.create_task(
                    email_service.send_welcome_email(to_email=user.email, user_name=user.first_name)
                )
        else:
            if user.status == UserStatus.SUSPENDED:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended")
            # Update avatar if not set
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            logger.info("Social login: existing user %s via %s", user.id, provider)

        # Update last login
        user.last_login = datetime.now(UTC)
        user.is_online = True
        await self.db.flush()

        # Generate tokens
        token_data = {"sub": str(user.id), "role": user.primary_role.value, "tv": user.token_version}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        expires = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        rt = RefreshToken(
            token_hash=self._hash_token(refresh_token),
            user_id=user.id,
            expires_at=expires,
        )
        self.db.add(rt)
        await self.db.flush()

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def _verify_google_token(self, access_token: str) -> tuple[str, str, str, str | None]:
        """Verify Google access token via userinfo endpoint and extract user info."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code != 200:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")
                data = resp.json()

            if "error" in data or not data.get("sub"):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

            email = data.get("email", "")
            name = data.get("name", "")
            first_name = data.get("given_name", "") or (name.split()[0] if name else "")
            last_name = data.get("family_name", "") or (" ".join(name.split()[1:]) if name else "")
            avatar_url = data.get("picture")
            return email, first_name, last_name, avatar_url
        except httpx.RequestError as e:
            logger.error("Google token verification failed: %s", e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not verify Google token") from e

    async def _verify_facebook_token(self, access_token: str) -> tuple[str, str, str, str | None]:
        """Verify Facebook access token and extract user info."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://graph.facebook.com/me",
                    params={
                        "fields": "id,email,first_name,last_name,picture.type(large)",
                        "access_token": access_token,
                    },
                )
                if resp.status_code != 200:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Facebook token")
                data = resp.json()

            if "error" in data:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Facebook token")

            email = data.get("email", "")
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            avatar_url = data.get("picture", {}).get("data", {}).get("url") if isinstance(data.get("picture"), dict) else None
            return email, first_name, last_name, avatar_url
        except httpx.RequestError as e:
            logger.error("Facebook token verification failed: %s", e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not verify Facebook token") from e

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

        # Validate token version — logout-all bumps this to invalidate old access tokens
        token_version = payload.get("tv", 0)
        if token_version != user.token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        return user

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """Generate new token pair from a valid refresh token."""
        # Check refresh token against DB before decoding
        token_hash = self._hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > datetime.now(UTC),
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

        # Generate new token pair (include current token_version)
        token_data = {"sub": str(user.id), "role": user.primary_role.value, "tv": user.token_version}
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        # Store new refresh token
        expires = datetime.now(UTC) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        new_rt = RefreshToken(
            token_hash=self._hash_token(new_refresh_token),
            user_id=user.id,
            expires_at=expires,
        )
        self.db.add(new_rt)
        await self.db.flush()

        logger.info("Token refreshed: user=%s", user.id)

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
        logger.info("User logged out: user=%s", user.id)

    async def logout_all(self, user: User) -> None:
        """Revoke all refresh tokens and invalidate all access tokens for the user."""
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
        )
        # Bump token_version to invalidate all outstanding access tokens immediately
        user.token_version += 1
        await self.db.flush()
        logger.info("All sessions terminated: user=%s", user.id)

    async def verify_email_token(self, token: str) -> None:
        """Verify email using JWT token."""
        try:
            payload = verify_email_token(token, "verify_email")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        user = await self._get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.is_email_verified:
            return  # Already verified - idempotent

        user.is_email_verified = True
        user.status = UserStatus.ACTIVE
        self.db.add(user)
        await self.db.commit()

    async def resend_verification(self, email: str, email_service) -> None:
        """Resend verification email. Silent if user not found (anti-enumeration)."""
        user = await self._get_user_by_email(email)
        if not user or user.is_email_verified:
            return
        token = create_email_token(str(user.id), "verify_email", 24 * 60)
        await email_service.send_verification_email(
            to_email=user.email,
            user_name=user.first_name,
            token=token,
        )

    async def request_password_reset(self, email: str, email_service) -> None:
        """Send password reset email. Silent if user not found (anti-enumeration)."""
        user = await self._get_user_by_email(email)
        if not user or user.status == UserStatus.SUSPENDED:
            return
        token = create_email_token(str(user.id), "password_reset", 60)
        await email_service.send_password_reset(
            to_email=user.email,
            user_name=user.first_name,
            token=token,
        )

    async def reset_password(self, token: str, new_password: str) -> None:
        """Reset password with JWT token."""
        try:
            payload = verify_email_token(token, "password_reset")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        user = await self._get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.hashed_password = await hash_password_async(new_password)
        user.token_version += 1  # Invalidate all existing sessions
        self.db.add(user)
        await self.db.commit()

    async def _get_user_by_email(self, email: str):
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: str):
        result = await self.db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        return result.scalar_one_or_none()

    async def send_phone_otp(self, phone: str, email_service) -> None:
        """Generate and send a 6-digit OTP. Delivers via email in beta (Twilio in production).
        Always returns silently if phone not found to prevent enumeration."""
        # Normalize: strip spaces; Iraqi numbers should start with +964
        phone = phone.strip()

        # Look up user by phone — silent if not found
        result = await self.db.execute(select(User).where(User.phone == phone, User.status == UserStatus.ACTIVE))
        user = result.scalar_one_or_none()
        if not user:
            return

        # Rate limit: max 3 OTPs per phone per 10 minutes
        ten_min_ago = datetime.now(UTC) - timedelta(minutes=10)
        count_result = await self.db.execute(
            select(func.count()).select_from(PhoneOtp).where(
                PhoneOtp.phone == phone,
                PhoneOtp.created_at > ten_min_ago,
            )
        )
        if (count_result.scalar() or 0) >= 3:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests. Please wait 10 minutes and try again.",
            )

        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()

        phone_otp = PhoneOtp(
            phone=phone,
            otp_hash=otp_hash,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        self.db.add(phone_otp)
        await self.db.flush()

        # Production: Twilio SMS. Beta fallback: deliver via user's email.
        if settings.TWILIO_ACCOUNT_SID.strip() and settings.TWILIO_AUTH_TOKEN.strip() and settings.TWILIO_PHONE_NUMBER.strip():
            from twilio.rest import Client as TwilioClient  # noqa: PLC0415
            twilio = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            twilio.messages.create(
                body=f"Kaasb رمز التحقق: {otp}\nصالح لمدة 10 دقائق. لا تشاركه مع أحد.",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone,
            )
            logger.info("Phone OTP sent via SMS to user=%s (phone=***%s)", user.id, phone[-4:])
        else:
            await email_service.send_phone_otp(
                to_email=user.email,
                otp_code=otp,
                phone=phone,
            )
            logger.info("Phone OTP sent via email to user=%s (phone=***%s)", user.id, phone[-4:])

    async def verify_phone_otp(self, phone: str, otp: str) -> TokenResponse:
        """Verify a phone OTP and return a token pair."""
        phone = phone.strip()
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        now = datetime.now(UTC)

        # Find a valid, unused OTP matching this phone + code
        result = await self.db.execute(
            select(PhoneOtp)
            .where(
                PhoneOtp.phone == phone,
                PhoneOtp.otp_hash == otp_hash,
                PhoneOtp.expires_at > now,
                PhoneOtp.is_used.is_(False),
            )
            .order_by(PhoneOtp.created_at.desc())
            .limit(1)
        )
        otp_record = result.scalar_one_or_none()

        if not otp_record:
            # Increment attempts on the most recent unexpired OTP to track brute-force
            recent_result = await self.db.execute(
                select(PhoneOtp)
                .where(
                    PhoneOtp.phone == phone,
                    PhoneOtp.expires_at > now,
                    PhoneOtp.is_used.is_(False),
                )
                .order_by(PhoneOtp.created_at.desc())
                .limit(1)
            )
            recent = recent_result.scalar_one_or_none()
            if recent:
                recent.attempts += 1
                if recent.attempts >= 5:
                    recent.is_used = True  # Lock after 5 wrong attempts
                await self.db.flush()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OTP")

        # Mark OTP as used (single-use)
        otp_record.is_used = True
        await self.db.flush()

        # Fetch user
        user_result = await self.db.execute(
            select(User).where(User.phone == phone, User.status == UserStatus.ACTIVE)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP")

        # Update last login
        user.last_login = now
        user.is_online = True
        await self.db.flush()

        # Issue token pair
        token_data = {"sub": str(user.id), "role": user.primary_role.value, "tv": user.token_version}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        rt = RefreshToken(
            token_hash=self._hash_token(refresh_token),
            user_id=user.id,
            expires_at=expires,
        )
        self.db.add(rt)
        await self.db.flush()

        logger.info("Phone OTP login successful: user=%s", user.id)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
