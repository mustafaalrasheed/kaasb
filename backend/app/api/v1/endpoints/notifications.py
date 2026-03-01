"""
Kaasb Platform - Notification Endpoints
"""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    NotificationDetail, NotificationListResponse,
    NotificationMarkRead, UnreadCount,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Get notifications",
)
async def get_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get notifications for the current user."""
    service = NotificationService(db)
    return await service.get_notifications(current_user, unread_only, page, page_size)


@router.get(
    "/unread-count",
    response_model=UnreadCount,
    summary="Get unread count",
)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get unread notification count."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user)
    return {"count": count}


@router.post(
    "/mark-read",
    summary="Mark notifications as read",
)
async def mark_notifications_read(
    data: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark specific notifications as read."""
    service = NotificationService(db)
    count = await service.mark_as_read(current_user, data.notification_ids)
    return {"marked": count}


@router.post(
    "/mark-all-read",
    summary="Mark all as read",
)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    service = NotificationService(db)
    count = await service.mark_all_read(current_user)
    return {"marked": count}
