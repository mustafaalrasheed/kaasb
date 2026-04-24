"""
Kaasb Platform - Authentication Service
Business logic for user registration, login, and token management.
"""

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import redis.asyncio as aioredis
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
DUMMY_HASH = "$2b$12$cGxpy3DvsqCEOfFbQdFt3./4QtwFLMnWFh8nB3cRKeGcW6olQmPK6"

_redis_client: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis | None:
    """Lazily create a shared Redis client. Returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            logger.warning("Redis unavailable in auth_service — token blacklist disabled")
    return _redis_client


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

    async def login(
        self,
        data: UserLogin,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
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

        # Social-only accounts (no password set) cannot use password login
        if not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="This account uses social login. Please sign in with Google or Facebook.",
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
            user_agent=(user_agent or "")[:500] or None,
            ip_address=ip_address,
            last_used_at=datetime.now(UTC),
        )
        self.db.add(rt)
        await self.db.commit()

        logger.info("Login successful: user=%s", user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def social_login(
        self,
        provider: str,
        token: str,
        role: str = "freelancer",
        email_service=None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Authenticate via Google or Facebook OAuth token."""
        # Verify token and fetch profile from provider
        if provider == "google":
            social_id, email, first_name, last_name, avatar_url = await self._verify_google_token(token)
        elif provider == "facebook":
            social_id, email, first_name, last_name, avatar_url = await self._verify_facebook_token(token)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not retrieve email from {provider}. Make sure email permission is granted.",
            )

        # 1. Look up by social ID first (prevents duplicate accounts)
        user = None
        if social_id:
            social_col = User.google_id if provider == "google" else User.facebook_id
            result = await self.db.execute(select(User).where(social_col == social_id))
            user = result.scalar_one_or_none()

        # 2. Fall back to email lookup
        if not user:
            result = await self.db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

        if not user:
            # Create new user from OAuth profile (no password needed)
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
                hashed_password=None,  # Social-only accounts have no password
                first_name=first_name or "User",
                last_name=last_name or "",
                avatar_url=avatar_url,
                primary_role=UserRole(role),
                status=UserStatus.ACTIVE,
                is_email_verified=True,
                google_id=social_id if provider == "google" else None,
                facebook_id=social_id if provider == "facebook" else None,
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
            # Link social ID if not yet stored (existing user, first social login)
            if social_id:
                if provider == "google" and not user.google_id:
                    user.google_id = social_id
                elif provider == "facebook" and not user.facebook_id:
                    user.facebook_id = social_id
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
            user_agent=(user_agent or "")[:500] or None,
            ip_address=ip_address,
            last_used_at=datetime.now(UTC),
        )
        self.db.add(rt)
        await self.db.commit()

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def _verify_google_token(self, access_token: str) -> tuple[str, str, str, str, str | None]:
        """Verify Google access token via userinfo endpoint and extract user info.
        Returns (google_id, email, first_name, last_name, avatar_url)."""
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

            google_id = data.get("sub", "")
            email = data.get("email", "")
            name = data.get("name", "")
            first_name = data.get("given_name", "") or (name.split()[0] if name else "")
            last_name = data.get("family_name", "") or (" ".join(name.split()[1:]) if name else "")
            avatar_url = data.get("picture")
            return google_id, email, first_name, last_name, avatar_url
        except httpx.RequestError as e:
            logger.error("Google token verification failed: %s", e)
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not verify Google token") from e

    async def _verify_facebook_token(self, access_token: str) -> tuple[str, str, str, str, str | None]:
        """Verify Facebook access token and extract user info.
        Returns (facebook_id, email, first_name, last_name, avatar_url)."""
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

            facebook_id = data.get("id", "")
            email = data.get("email", "")
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            avatar_url = data.get("picture", {}).get("data", {}).get("url") if isinstance(data.get("picture"), dict) else None
            return facebook_id, email, first_name, last_name, avatar_url
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

    # Grace period (seconds) for recently-rotated refresh tokens.
    # During rotation, the old token is revoked and a new one issued. If a
    # concurrent request (e.g. notification poll) races with the refresh, it
    # may re-send the old token before the browser stores the new cookie.
    # Instead of hard-failing (which logs the user out), we detect this race
    # and issue fresh tokens from the same session.
    _ROTATION_GRACE_SECONDS = 60

    async def refresh_tokens(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenResponse:
        """Generate new token pair from a valid refresh token."""
        # Check refresh token against DB before decoding
        token_hash = self._hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.expires_at > datetime.now(UTC),
            )
        )
        stored_token = result.scalar_one_or_none()
        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Handle rotation race: token was JUST revoked by a concurrent refresh.
        # Find the replacement token (same user, created right after revocation)
        # and use it instead of failing outright.
        if stored_token.revoked:
            grace_cutoff = datetime.now(UTC) - timedelta(seconds=self._ROTATION_GRACE_SECONDS)
            if stored_token.updated_at < grace_cutoff:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token",
                )
            # Within grace window — find the newest active token for this user
            latest_result = await self.db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == stored_token.user_id,
                    RefreshToken.revoked.is_(False),
                    RefreshToken.expires_at > datetime.now(UTC),
                ).order_by(RefreshToken.created_at.desc()).limit(1)
            )
            replacement = latest_result.scalar_one_or_none()
            if not replacement:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token",
                )
            logger.info("Rotation grace: reusing replacement token for user=%s", stored_token.user_id)
            stored_token = replacement

        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type - expected refresh token",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        try:
            user_uuid = uuid.UUID(user_id)
        except (ValueError, AttributeError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            ) from e
        result = await self.db.execute(
            select(User).where(User.id == user_uuid)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
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
            user_agent=((user_agent or stored_token.user_agent) or "")[:500] or None,
            ip_address=ip_address or stored_token.ip_address,
            last_used_at=datetime.now(UTC),
        )
        self.db.add(new_rt)
        await self.db.commit()

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

    async def list_sessions(self, user: User) -> list[RefreshToken]:
        """List active (non-revoked, non-expired) refresh tokens for the user."""
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_other_sessions(
        self, user: User, keep_token_hash: str | None
    ) -> int:
        """Revoke all active sessions for the user EXCEPT the one identified
        by ``keep_token_hash``. Returns how many were revoked.

        Used by the "Log out of other devices" button in /dashboard/settings:
        users who travel + login on multiple phones accumulate many active
        refresh tokens (7-day expiry), and pruning them one-by-one is tedious.
        Current device stays signed-in; all others are invalidated.
        """
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
                RefreshToken.expires_at > now,
            )
        )
        all_active = list(result.scalars().all())
        revoked = 0
        for rt in all_active:
            if keep_token_hash is not None and rt.token_hash == keep_token_hash:
                continue
            rt.revoked = True
            revoked += 1
        await self.db.commit()
        return revoked

    async def revoke_session(self, user: User, session_id: uuid.UUID) -> None:
        """Revoke a single refresh token owned by the user."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.id == session_id,
                RefreshToken.user_id == user.id,
            )
        )
        token = result.scalar_one_or_none()
        if not token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        token.revoked = True
        await self.db.commit()

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

        # Single-use enforcement: check if this jti has already been used.
        # Without this, an attacker who intercepts the reset email can replay the token
        # repeatedly within its 60-minute window to override the legitimate user's password.
        jti = payload.get("jti")
        redis = await _get_redis()
        if jti and redis:
            try:
                already_used = await redis.get(f"used_reset_jti:{jti}")
                if already_used:
                    raise HTTPException(status_code=400, detail="Password reset link has already been used")
            except HTTPException:
                raise
            except Exception:
                pass  # Redis down: allow the reset (availability > strict single-use when infra is degraded)

        user = await self._get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.hashed_password = await hash_password_async(new_password)
        # Rotate sessions: bump token_version (invalidates access tokens) AND
        # revoke all outstanding refresh tokens (otherwise an attacker with a
        # live refresh token could immediately mint a new access token).
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
        )
        user.token_version += 1
        self.db.add(user)
        await self.db.commit()

        # Blacklist the jti so this token cannot be replayed
        if jti and redis:
            try:
                exp = payload.get("exp", 0)
                ttl = max(1, int(exp - datetime.now(UTC).timestamp()))
                await redis.setex(f"used_reset_jti:{jti}", ttl, "1")
            except Exception:
                pass  # Non-fatal: token_version bump already limits damage

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

        # Generate 6-digit OTP using OS CSPRNG (not random.randint which is predictable)
        otp = str(secrets.randbelow(900000) + 100000)
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()

        phone_otp = PhoneOtp(
            phone=phone,
            otp_hash=otp_hash,
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
        self.db.add(phone_otp)
        await self.db.flush()

        # OTP delivery priority:
        #   1. WhatsApp (TWILIO_WHATSAPP_NUMBER set)  — best UX for Iraqi market
        #   2. SMS      (TWILIO_PHONE_NUMBER set)     — fallback
        #   3. Email                                  — beta / infra not configured yet
        # Twilio SDK is synchronous — run in thread pool to avoid blocking the event loop.
        has_twilio = bool(
            settings.TWILIO_ACCOUNT_SID.strip()
            and settings.TWILIO_AUTH_TOKEN.strip()
        )
        otp_body = f"Kaasb رمز التحقق: {otp}\nصالح لمدة 10 دقائق. لا تشاركه مع أحد."

        if has_twilio and settings.TWILIO_WHATSAPP_NUMBER.strip():
            import asyncio as _asyncio

            from twilio.rest import Client as TwilioClient  # noqa: PLC0415

            def _send_whatsapp() -> None:
                TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN).messages.create(
                    body=otp_body,
                    from_=settings.TWILIO_WHATSAPP_NUMBER.strip(),
                    to=f"whatsapp:{phone}",
                )

            loop = _asyncio.get_running_loop()
            await loop.run_in_executor(None, _send_whatsapp)
            logger.info("Phone OTP sent via WhatsApp to user=%s (phone=***%s)", user.id, phone[-4:])

        elif has_twilio and settings.TWILIO_PHONE_NUMBER.strip():
            import asyncio as _asyncio

            from twilio.rest import Client as TwilioClient  # noqa: PLC0415

            def _send_sms() -> None:
                TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN).messages.create(
                    body=otp_body,
                    from_=settings.TWILIO_PHONE_NUMBER.strip(),
                    to=phone,
                )

            loop = _asyncio.get_running_loop()
            await loop.run_in_executor(None, _send_sms)
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
