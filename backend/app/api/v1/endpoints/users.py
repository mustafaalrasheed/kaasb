"""
Kaasb Platform - User Profile Endpoints
GET    /users/freelancers          - Search freelancers
GET    /users/profile/{username}   - View public profile
PUT    /users/profile              - Update own profile
POST   /users/avatar               - Upload avatar
DELETE /users/avatar               - Remove avatar
PUT    /users/password             - Change password
DELETE /users/account              - Deactivate account
"""


from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    UserListResponse,
    UserMe,
    UserProfile,
    UserProfileUpdate,
)
from app.services.user_service import UserService
from app.utils.files import delete_avatar, save_avatar

router = APIRouter(prefix="/users", tags=["Users"])


# === Public Endpoints ===


@router.get(
    "/freelancers",
    response_model=UserListResponse,
    summary="Search and browse freelancers",
)
async def search_freelancers(
    q: str | None = Query(None, description="Search by name, title, bio"),
    skills: str | None = Query(
        None, description="Comma-separated skills filter"
    ),
    experience_level: str | None = Query(
        None, pattern=r"^(entry|intermediate|expert)$"
    ),
    country: str | None = Query(None),
    sort_by: str = Query("rating", pattern=r"^(rating|newest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Browse and search freelancers with filters.

    - **q**: Text search across name, title, bio
    - **skills**: Comma-separated list (e.g., "Python,React,Design")
    - **experience_level**: entry, intermediate, or expert
    - **country**: Filter by country
    - **sort_by**: rating (default), newest
    """
    service = UserService(db)
    skills_list = [s.strip() for s in skills.split(",")] if skills else None

    return await service.search_freelancers(
        query=q,
        skills=skills_list,
        experience_level=experience_level,
        country=country,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/profile/{username}",
    response_model=UserProfile,
    summary="Get public user profile",
)
async def get_user_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a user's public profile by username."""
    service = UserService(db)
    return await service.get_by_username(username)


# === Authenticated Endpoints ===


@router.put(
    "/profile",
    response_model=UserMe,
    summary="Update your profile",
)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the authenticated user's profile.
    Only send the fields you want to update.
    Freelancer-specific fields (title, skills, experience_level, etc.)
    are only available for freelancer accounts.
    """
    service = UserService(db)
    return await service.update_profile(current_user, data)


@router.put(
    "/me/locale",
    summary="Update the authenticated user's preferred UI locale",
)
async def update_my_locale(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persist the authenticated user's preferred UI locale. Used by the
    server-side notification service to pick the right title/message at
    emission time. Accepts {"locale": "ar" | "en"}; other values reject.
    """
    locale = (payload or {}).get("locale", "").strip().lower()
    if locale not in ("ar", "en"):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="locale must be 'ar' or 'en'",
        )
    current_user.locale = locale
    await db.commit()
    return {"locale": locale}


@router.post(
    "/avatar",
    response_model=UserMe,
    summary="Upload profile avatar",
)
async def upload_avatar(
    file: UploadFile = File(..., description="Avatar image (JPEG, PNG, WebP, max 10MB)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload or replace the user's avatar image."""
    # Delete old avatar file if exists
    delete_avatar(current_user.avatar_url)

    # Save new avatar
    avatar_url = await save_avatar(file, str(current_user.id))

    # Update user record
    service = UserService(db)
    return await service.update_avatar(current_user, avatar_url)


@router.delete(
    "/avatar",
    response_model=UserMe,
    summary="Remove profile avatar",
)
async def remove_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove the user's avatar image."""
    delete_avatar(current_user.avatar_url)

    service = UserService(db)
    return await service.remove_avatar(current_user)


@router.put(
    "/password",
    status_code=status.HTTP_200_OK,
    summary="Change password",
)
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's password."""
    service = UserService(db)
    await service.change_password(current_user, data)
    return {"detail": "Password changed successfully"}


@router.delete(
    "/account",
    status_code=status.HTTP_200_OK,
    summary="Deactivate account",
)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate the authenticated user's account.
    This is a soft delete - the account can be reactivated.
    """
    service = UserService(db)
    await service.deactivate_account(current_user)
    return {"detail": "Account deactivated successfully"}
