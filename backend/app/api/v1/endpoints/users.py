"""
Kaasb Platform - User Profile Endpoints
GET    /users/freelancers          - Search freelancers
GET    /users/profile/{username}   - View public profile
PUT    /users/profile              - Update own profile
POST   /users/avatar               - Upload avatar
DELETE /users/avatar               - Remove avatar
PUT    /users/password             - Change password
DELETE /users/account              - Deactivate account
GET    /users/unsubscribe          - One-click email opt-out (token-signed, no login)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.security import verify_email_token
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

logger = logging.getLogger(__name__)

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


@router.get(
    "/me/email-preferences",
    summary="Read the authenticated user's email notification preferences",
)
async def get_my_email_preferences(
    current_user: User = Depends(get_current_user),
):
    """Return the per-user email toggle. Granular per-type preferences are
    intentionally not exposed yet — one toggle covers the whitelist of
    high-signal notification types the server opts into."""
    return {"email_notifications_enabled": current_user.email_notifications_enabled}


@router.put(
    "/me/email-preferences",
    summary="Update the authenticated user's email notification preferences",
)
async def update_my_email_preferences(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle whether the user receives email copies of notifications.
    Accepts {"email_notifications_enabled": bool}; everything else rejects."""
    value = (payload or {}).get("email_notifications_enabled")
    if not isinstance(value, bool):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email_notifications_enabled must be a boolean",
        )
    current_user.email_notifications_enabled = value
    await db.commit()
    return {"email_notifications_enabled": value}


# Public, no-auth unsubscribe endpoint. The email's footer link points here
# with a per-recipient signed JWT (type="unsubscribe", 30-day expiry). Hitting
# this URL flips email_notifications_enabled=false and renders a minimal
# bilingual confirmation page — no login required, deliverable to anyone who
# just wants to stop the email noise (chat-notifications-audit 3.3).

_UNSUBSCRIBE_OK_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unsubscribed — Kaasb</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Tahoma,Arial,sans-serif;
background:#f4f7f9;color:#1a1a2e;margin:0;padding:40px 20px;}}
.card{{max-width:520px;margin:0 auto;background:#fff;border-radius:12px;
padding:36px 32px;box-shadow:0 2px 8px rgba(0,0,0,0.06);text-align:center;}}
h1{{font-size:22px;margin:0 0 16px;color:#2188cb;}}
p{{font-size:15px;line-height:1.7;color:#555;margin:0 0 12px;}}
.ar{{direction:rtl;text-align:right;border-top:1px solid #e8ecef;
margin-top:24px;padding-top:24px;font-family:Tahoma,Arial,sans-serif;}}
a{{color:#2188cb;text-decoration:none;font-weight:600;}}
</style></head><body><div class="card">
<h1>You're unsubscribed.</h1>
<p>You won't get email copies of in-app notifications from Kaasb anymore.
You'll still see them in the bell icon when you sign in.</p>
<p>Changed your mind? <a href="{frontend_url}/dashboard/settings">Re-enable
in your settings</a>.</p>
<div class="ar"><h1>تم إلغاء الاشتراك.</h1>
<p>لن تتلقى نسخاً بريدية من إشعارات كاسب بعد الآن. ستبقى الإشعارات
متاحة عبر الجرس عند تسجيل دخولك.</p>
<p>هل غيّرت رأيك؟ <a href="{frontend_url}/dashboard/settings">أعد التفعيل
من الإعدادات</a>.</p></div></div></body></html>
"""

_UNSUBSCRIBE_BAD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Link expired — Kaasb</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Tahoma,Arial,sans-serif;
background:#f4f7f9;color:#1a1a2e;margin:0;padding:40px 20px;}}
.card{{max-width:520px;margin:0 auto;background:#fff;border-radius:12px;
padding:36px 32px;box-shadow:0 2px 8px rgba(0,0,0,0.06);text-align:center;}}
h1{{font-size:22px;margin:0 0 16px;color:#c44569;}}
p{{font-size:15px;line-height:1.7;color:#555;margin:0 0 12px;}}
a{{color:#2188cb;text-decoration:none;font-weight:600;}}
</style></head><body><div class="card">
<h1>This unsubscribe link isn't valid anymore.</h1>
<p>It may have expired (links work for 30 days) or already been used.
You can manage email preferences directly in your account.</p>
<p><a href="{frontend_url}/dashboard/settings">Open settings</a></p>
</div></body></html>
"""


@router.get(
    "/unsubscribe",
    response_class=HTMLResponse,
    include_in_schema=False,  # not part of the public API surface
    summary="One-click email-notification opt-out (signed token, no login)",
)
async def unsubscribe_via_token(
    token: str = Query(..., min_length=10, description="Signed unsubscribe token from a notification email"),
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint reachable from the unsubscribe link in any
    notification email. Verifies the JWT, flips the recipient's
    ``email_notifications_enabled`` to false, returns a minimal bilingual
    confirmation page.

    Idempotent: re-clicking the same link silently re-applies the false
    flag — never returns an error if the user is already opted out.
    Bad / expired tokens render a friendly "link expired" page so the
    user can self-serve from their settings.
    """
    from app.core.config import get_settings
    settings = get_settings()

    try:
        payload = verify_email_token(token, expected_type="unsubscribe")
    except ValueError as exc:
        logger.info("unsubscribe: invalid token: %s", exc)
        return HTMLResponse(
            _UNSUBSCRIBE_BAD_HTML.format(frontend_url=settings.FRONTEND_URL),
            status_code=400,
        )

    user_id_raw = payload.get("sub")
    try:
        user_id = uuid.UUID(str(user_id_raw))
    except (TypeError, ValueError):
        logger.info("unsubscribe: token missing/invalid sub claim")
        return HTMLResponse(
            _UNSUBSCRIBE_BAD_HTML.format(frontend_url=settings.FRONTEND_URL),
            status_code=400,
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        # User deleted between email send and click — treat as success
        # to avoid leaking account-existence info.
        return HTMLResponse(
            _UNSUBSCRIBE_OK_HTML.format(frontend_url=settings.FRONTEND_URL),
        )

    if user.email_notifications_enabled:
        user.email_notifications_enabled = False
        await db.commit()
        logger.info("unsubscribe: opted out user=%s", user_id)
    return HTMLResponse(
        _UNSUBSCRIBE_OK_HTML.format(frontend_url=settings.FRONTEND_URL),
    )


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
