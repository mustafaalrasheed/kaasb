"""
Kaasb Platform - Notification Service
Create and manage in-app notifications.

Localization:
  create_notification resolves the target user's locale at emission time
  using users.locale (default 'ar'). Callers pass both Arabic and English
  strings; the resolved copy is persisted to the notifications table. If
  the user later changes their locale preference, already-stored
  notifications keep their original copy — we don't re-render history.
"""

import asyncio
import logging
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.services.base import BaseService
from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

# Note: Notification queries intentionally do NOT load the user relationship —
# the endpoint already knows the user from auth context, avoiding wasteful JOINs.

# Supported locales. Adding a new one requires updating every notify() caller
# to pass the new string — the enum enforces completeness at signature time.
_SUPPORTED_LOCALES = ("ar", "en")
_DEFAULT_LOCALE = "ar"


def _bump_dispatch(channel: str, status: str) -> None:
    """Increment the notification dispatch counter. Guarded so a metrics
    import failure never blocks the actual delivery path."""
    try:
        from app.middleware.monitoring import NOTIFICATION_DISPATCH_TOTAL
        NOTIFICATION_DISPATCH_TOTAL.labels(channel=channel, status=status).inc()
    except Exception:
        pass


def _push_read_event(user_id: uuid.UUID, *, marked: int, all: bool) -> None:
    """Broadcast a notification_read WS event so other tabs/devices decrement
    their bell without waiting for the next poll. Fire-and-forget — missed
    events degrade to a slightly stale badge, not a correctness bug."""
    payload = {
        "type": "notification_read",
        "data": {"marked": marked, "all": all},
    }
    try:
        asyncio.create_task(manager.send_to_user(user_id, payload))
    except Exception:
        logger.debug("notification_read WS emit failed", exc_info=True)


async def _resolve_locale(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Fetch the target user's preferred UI locale. Defaults to 'ar' when the
    user is missing or the locale column is null/invalid so a DB hiccup never
    blocks a notification."""
    try:
        result = await db.execute(select(User.locale).where(User.id == user_id))
        locale = (result.scalar_one_or_none() or _DEFAULT_LOCALE).lower()
    except Exception:
        logger.warning("locale: failed to load for user=%s, defaulting to 'ar'", user_id)
        return _DEFAULT_LOCALE
    return locale if locale in _SUPPORTED_LOCALES else _DEFAULT_LOCALE


class NotificationService(BaseService):
    """Service for notification operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def create_notification(
        self,
        user_id: uuid.UUID,
        type: NotificationType,
        title_ar: str,
        title_en: str,
        message_ar: str,
        message_en: str,
        link_type: str | None = None,
        # Accept str in addition to UUID: many callers already stringify the
        # id (e.g. str(order_id)) and PostgreSQL UUID columns accept either.
        link_id: uuid.UUID | str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> Notification:
        """Create a notification for a user in their preferred locale.

        Both Arabic and English copy must be supplied. The user's locale
        preference (users.locale) decides which pair is persisted and pushed.
        """
        locale = await _resolve_locale(self.db, user_id)
        title = title_en if locale == "en" else title_ar
        message = message_en if locale == "en" else message_ar

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
        try:
            await self.db.flush()
        except Exception:
            _bump_dispatch("in_app", "fail")
            raise
        _bump_dispatch("in_app", "ok")

        # Push real-time event to the user via WebSocket (non-blocking).
        # WS delivery is best-effort — a user who's offline will still see
        # the notification on next fetch; we only count failures for
        # observability, never retry.
        ws_payload = {
            "type": "notification",
            "data": {
                "id": str(notification.id),
                "title": title,
                "message": message,
                "type": type.value,
                "link_type": link_type,
                "link_id": str(link_id) if link_id else None,
                "created_at": notification.created_at.isoformat(),
            },
        }

        async def _send_ws() -> None:
            try:
                await manager.send_to_user(user_id, ws_payload)
                _bump_dispatch("ws", "ok")
            except Exception:
                _bump_dispatch("ws", "fail")
                logger.debug("WS notification push failed", exc_info=True)

        asyncio.create_task(_send_ws())

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
                # Only flip UNREAD → READ so the rowcount we return + the WS
                # decrement is accurate.
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self.db.flush()
        marked = result.rowcount or 0
        if marked:
            _push_read_event(user.id, marked=marked, all=False)
        return marked

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
        marked = result.rowcount or 0
        if marked:
            _push_read_event(user.id, marked=marked, all=True)
        return marked


# === Notification helpers ===

async def notify(
    db,
    user_id: uuid.UUID,
    type: NotificationType,
    title_ar: str,
    title_en: str,
    message_ar: str,
    message_en: str,
    link_type: str | None = None,
    link_id: uuid.UUID | str | None = None,
    actor_id: uuid.UUID | None = None,
) -> Notification:
    """Send a notification using an existing DB session (in-request context)."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=user_id,
        type=type,
        title_ar=title_ar,
        title_en=title_en,
        message_ar=message_ar,
        message_en=message_en,
        link_type=link_type,
        link_id=link_id,
        actor_id=actor_id,
    )


async def notify_background(
    user_id: uuid.UUID,
    type: NotificationType,
    title_ar: str,
    title_en: str,
    message_ar: str,
    message_en: str,
    link_type: str | None = None,
    link_id: uuid.UUID | str | None = None,
    actor_id: uuid.UUID | None = None,
) -> None:
    """
    Send a notification from a background asyncio task using its own DB session.

    Use this instead of notify() when scheduling via asyncio.create_task(), because
    the request's session may be closed by get_db() before the task executes.
    Each call opens and commits a dedicated session so there is no shared-state race.
    """
    from app.core.database import async_session  # late import avoids circular deps

    try:
        async with async_session() as session:
            service = NotificationService(session)
            await service.create_notification(
                user_id=user_id,
                type=type,
                title_ar=title_ar,
                title_en=title_en,
                message_ar=message_ar,
                message_en=message_en,
                link_type=link_type,
                link_id=link_id,
                actor_id=actor_id,
            )
            await session.commit()
    except Exception as exc:
        logger.warning(
            "Background notification failed: user=%s type=%s error=%s",
            user_id, type.value, exc,
        )
