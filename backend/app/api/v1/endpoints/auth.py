"""
Kaasb Platform - Authentication Endpoints
POST /auth/register            - Create new account
POST /auth/login               - Get JWT tokens
POST /auth/refresh             - Refresh JWT tokens
GET  /auth/me                  - Get current user profile
POST /auth/logout              - Revoke current refresh token
POST /auth/logout-all          - Revoke all refresh tokens (all sessions)
POST /auth/verify-email        - Verify email address with token
POST /auth/resend-verification - Resend email verification
POST /auth/forgot-password     - Request password reset email
POST /auth/reset-password      - Reset password with token
"""

import asyncio

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    PhoneOtpRequest,
    PhoneOtpVerifyRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    SocialLoginRequest,
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserMe,
    UserRegister,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly cookies for access and refresh tokens."""
    is_secure = settings.ENVIRONMENT != "development"  # Secure for production AND staging
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",  # Only sent to auth endpoints
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies on logout."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user account and return JWT tokens.

    - **email**: Valid email address (unique)
    - **username**: 3-50 characters, alphanumeric with _ and - (unique)
    - **password**: Min 8 chars with uppercase, digit, and special character
    - **primary_role**: "client" or "freelancer"
    """
    auth_service = AuthService(db)
    await auth_service.register(data)

    # Auto-login after registration
    login_data = UserLogin(email=data.email, password=data.password)
    tokens = await auth_service.login(login_data)
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)

    # Send welcome email in background (non-blocking; MVP auto-verifies email)
    email_service = EmailService()
    user = await auth_service._get_user_by_email(data.email)
    if user:
        asyncio.create_task(
            email_service.send_welcome_email(
                to_email=user.email,
                user_name=user.first_name,
            )
        )

    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
async def login(
    data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email and password, receive JWT token pair.
    Tokens are also set as httpOnly cookies.
    """
    auth_service = AuthService(db)
    tokens = await auth_service.login(data)
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh JWT tokens",
)
async def refresh_token(
    data: TokenRefresh,
    response: Response,
    refresh_token_cookie: str | None = Cookie(default=None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new token pair.
    Token is read from the httpOnly cookie (preferred) or the request body.
    Tokens are also set as httpOnly cookies.
    """
    # Prefer the httpOnly cookie — the browser sends it automatically.
    # Fall back to the request body for API clients that manage tokens manually.
    token = refresh_token_cookie or data.refresh_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_tokens(token)
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post(
    "/clear-session",
    status_code=status.HTTP_200_OK,
    summary="Clear auth cookies (no authentication required)",
    include_in_schema=False,
)
async def clear_session(response: Response):
    """
    Clear access_token and refresh_token cookies without requiring a valid token.
    Called by the frontend when a refresh fails and we need to wipe stale cookies
    so the middleware stops redirecting the user back to protected routes.
    """
    _clear_auth_cookies(response)
    return {"ok": True}


@router.get(
    "/me",
    response_model=UserMe,
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the authenticated user's full profile including private fields.
    """
    return current_user


@router.post("/logout", summary="Logout (revoke current refresh token)")
async def logout(
    data: TokenRefresh,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the provided refresh token and clear auth cookies."""
    service = AuthService(db)
    await service.logout(current_user, data.refresh_token)
    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post(
    "/social",
    response_model=TokenResponse,
    summary="Login or register via Google/Facebook",
)
async def social_login(
    data: SocialLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate using a Google ID token or Facebook access token.
    Creates a new account automatically if the email is not registered.
    """
    service = AuthService(db)
    email_service = EmailService()
    tokens = await service.social_login(data.provider, data.token, data.role, email_service=email_service)
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens


@router.post("/logout-all", summary="Logout all sessions")
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all refresh tokens for the current user."""
    service = AuthService(db)
    await service.logout_all(current_user)
    return {"message": "All sessions terminated"}


@router.post("/verify-email", summary="Verify email address with token")
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify email using the token sent to the user's inbox."""
    auth_service = AuthService(db)
    await auth_service.verify_email_token(data.token)
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification", summary="Resend email verification")
async def resend_verification(
    data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resend verification email. Rate limited to 3 per hour per email."""
    auth_service = AuthService(db)
    email_service = EmailService()
    await auth_service.resend_verification(data.email, email_service)
    # Always return success to prevent email enumeration
    return {"message": "If the email exists and is unverified, a new verification link has been sent."}


@router.post("/forgot-password", summary="Request password reset email")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send password reset email. Always returns success (prevents email enumeration)."""
    auth_service = AuthService(db)
    email_service = EmailService()
    await auth_service.request_password_reset(data.email, email_service)
    return {"message": "If the email exists, a password reset link has been sent."}


@router.post("/reset-password", summary="Reset password with token")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using the token from the reset email. Token is single-use."""
    auth_service = AuthService(db)
    await auth_service.reset_password(data.token, data.new_password)
    return {"message": "Password reset successfully. Please log in with your new password."}


@router.post("/ws-ticket", summary="Get a short-lived WebSocket auth ticket")
async def get_ws_ticket(current_user: User = Depends(get_current_user)):
    """
    Returns a 60-second, single-use ticket for authenticating the WebSocket connection.
    Solves the httpOnly cookie problem: the browser cannot pass cookies to a cross-origin
    WebSocket, so instead the frontend calls this endpoint (cookie-authenticated) to get
    an opaque ticket it can safely pass as a URL query parameter.
    """
    from app.services.websocket_manager import create_ws_ticket
    ticket = await create_ws_ticket(current_user.id)
    return {"ticket": ticket, "expires_in": 60}


@router.post("/phone/send-otp", summary="Send OTP to phone number (email delivery in beta)")
async def send_phone_otp(
    data: PhoneOtpRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a 6-digit OTP to the user's email address linked to their phone number.
    Beta mode: delivered via email. Production: Twilio SMS.
    Always returns success to prevent phone enumeration.
    Rate limited to 3 requests per phone per 10 minutes.
    """
    auth_service = AuthService(db)
    email_service = EmailService()
    await auth_service.send_phone_otp(data.phone, email_service)
    return {"message": "If this phone number is registered, an OTP has been sent."}


@router.post("/phone/verify-otp", response_model=TokenResponse, summary="Verify phone OTP and get tokens")
async def verify_phone_otp(
    data: PhoneOtpVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify the 6-digit OTP and return a JWT token pair.
    OTP is single-use and expires after 10 minutes.
    Account is locked after 5 consecutive wrong attempts.
    """
    auth_service = AuthService(db)
    tokens = await auth_service.verify_phone_otp(data.phone, data.otp)
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return tokens
