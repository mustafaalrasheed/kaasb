"""
Kaasb Platform - Dependencies
Reusable FastAPI dependencies for authentication and authorization.
"""

from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import oauth2_scheme
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


async def _extract_token(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    access_token: Optional[str] = Cookie(default=None),
) -> str:
    """Extract JWT token from Authorization header or httpOnly cookie."""
    # Prefer Authorization header, fall back to cookie
    if token:
        return token
    if access_token:
        return access_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(_extract_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the currently authenticated user."""
    auth_service = AuthService(db)
    return await auth_service.get_current_user(token)


async def get_current_freelancer(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be a freelancer."""
    if current_user.primary_role != UserRole.FREELANCER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a freelancer account",
        )
    return current_user


async def get_current_client(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be a client."""
    if current_user.primary_role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a client account",
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to be an admin."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
