"""
Kaasb Platform - Authentication Endpoints
POST /auth/register     - Create new account
POST /auth/login        - Get JWT tokens
POST /auth/refresh      - Refresh JWT tokens
GET  /auth/me           - Get current user profile
POST /auth/logout       - Revoke current refresh token
POST /auth/logout-all   - Revoke all refresh tokens (all sessions)
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserMe,
)
from app.services.auth_service import AuthService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account and return JWT tokens.

    - **email**: Valid email address (unique)
    - **username**: 3-50 characters, alphanumeric with _ and - (unique)
    - **password**: Min 8 chars with uppercase, digit, and special character
    - **primary_role**: "client" or "freelancer"
    """
    auth_service = AuthService(db)
    user = await auth_service.register(data)

    # Auto-login after registration
    login_data = UserLogin(email=data.email, password=data.password)
    return await auth_service.login(login_data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate with email and password, receive JWT token pair.
    """
    auth_service = AuthService(db)
    return await auth_service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh JWT tokens",
)
async def refresh_token(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """
    Exchange a valid refresh token for a new token pair.
    """
    auth_service = AuthService(db)
    return await auth_service.refresh_tokens(data.refresh_token)


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the provided refresh token."""
    service = AuthService(db)
    await service.logout(current_user, data.refresh_token)
    return {"message": "Logged out successfully"}


@router.post("/logout-all", summary="Logout all sessions")
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all refresh tokens for the current user."""
    service = AuthService(db)
    await service.logout_all(current_user)
    return {"message": "All sessions terminated"}
