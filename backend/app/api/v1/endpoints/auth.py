"""
Kaasb Platform - Authentication Endpoints
POST /auth/register  - Create new account
POST /auth/login     - Get JWT tokens
POST /auth/refresh   - Refresh JWT tokens
GET  /auth/me        - Get current user profile
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
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
@limiter.limit("5/minute")
async def register(request: Request, data: UserRegister, db: AsyncSession = Depends(get_db)):
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
    return await auth_service.login(login_data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
@limiter.limit("10/minute")
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("20/minute")
async def refresh_token(request: Request, data: TokenRefresh, db: AsyncSession = Depends(get_db)):
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
