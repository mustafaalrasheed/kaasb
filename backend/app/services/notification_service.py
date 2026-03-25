"""
Kaasb Platform - Notification Service
Create and manage in-app notifications.
"""

import uuid
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.base import BaseService

# Note: Notification queries intentionally do NOT load the user relationship —
# the endpoint already knows the user from auth context, avoiding wasteful JOINs.


class NotificationService(BaseService):
    """Service for notification operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create_notification(
        self,
        user_id: uuid.UUID,
        type: NotificationType,
        title: str,
        message: str,
        link_type: Optional[str] = None,
        link_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        """Create a notification for a user."""
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link_type=link_type,
            link_id=link_id,
            actor_id=actor_id,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def get_notifications(
        self,
        user: User,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get notifications for a user."""
        page_size = self.clamp_page_size(page_size)
        stmt = select(Notification).where(Notification.user_id == user.id)

        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Unread count (always)
        unread_result = await self.db.execute(
            select(func.count()).where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            )
        )
        unread_count = unread_result.scalar() or 0

        # Paginate
        stmt = stmt.order_by(Notification.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        notifications = list(result.scalars().all())

        result_dict = self.paginated_response(items=notifications, total=total, page=page, page_size=page_size, key="notifications")
        result_dict["unread_count"] = unread_count
        return result_dict

    async def get_unread_count(self, user: User) -> int:
        """Get unread notification count."""
        result = await self.db.execute(
            select(func.count()).where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalar() or 0

    async def mark_as_read(
        self, user: User, notification_ids: list[uuid.UUID]
    ) -> int:
        """Mark specific notifications as read."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.user_id == user.id,
            )
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount

    async def mark_all_read(self, user: User) -> int:
        """Mark all notifications as read."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount


# === Helper: Send notification from anywhere in the app ===

async def notify(
    db,
    user_id: uuid.UUID,
    type: NotificationType,
    title: str,
    message: str,
    **kwargs,
) -> Notification:
    """Convenience function to send a notification."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        **kwargs,
    )
