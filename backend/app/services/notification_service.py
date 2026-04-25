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

from app.core.config import get_settings
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

# Notification types that also trigger an email copy, when the recipient has
# email_notifications_enabled. Intentionally a short high-signal whitelist —
# the bell already covers routine activity. Everything not in this set is
# in-app only.
_EMAILABLE_TYPES = frozenset({
    NotificationType.PROPOSAL_ACCEPTED,
    NotificationType.CONTRACT_CREATED,
    NotificationType.MILESTONE_FUNDED,
    NotificationType.MILESTONE_APPROVED,
    NotificationType.PAYMENT_RECEIVED,
    NotificationType.PAYOUT_COMPLETED,
    NotificationType.DISPUTE_OPENED,
    NotificationType.DISPUTE_RESOLVED,
    NotificationType.BUYER_REQUEST_OFFER_ACCEPTED,
})

# Link types that map to a stable URL suitable for email deep-linking. Frontend
# route shape matches the notifications page's getLink helper.
_EMAIL_LINK_ROUTES = {
    "contract": "/dashboard/contracts/{id}",
    "job": "/jobs/{id}",
    "gig": "/dashboard/gigs",
    "gig_order": "/dashboard/gigs/orders?order={id}",
    "buyer_request": "/dashboard/requests?highlight={id}",
    "proposal": "/dashboard/my-proposals",
    "message": "/dashboard/messages",
}


def _bump_dispatch(channel: str, status: str) -> None:
    """Increment the notification dispatch counter. Guarded so a metrics
    import failure never blocks the actual delivery path."""
    try:
        from app.middleware.monitoring import NOTIFICATION_DISPATCH_TOTAL
        NOTIFICATION_DISPATCH_TOTAL.labels(channel=channel, status=status).inc()
    except Exception:
        pass


def _build_link_url(link_type: str | None, link_id) -> str | None:
    """Map a notification's (link_type, link_id) to an absolute frontend URL
    suitable for the email deep-link. Returns None when no template is
    registered for the link_type — the email then omits the CTA button."""
    if not link_type:
        return None
    template = _EMAIL_LINK_ROUTES.get(link_type)
    if not template:
        return None
    base = get_settings().FRONTEND_URL.rstrip("/")
    path = template.format(id=link_id) if link_id else template.split("?")[0]
    return f"{base}{path}"


async def _send_notification_email_bg(
    *,
    email: str,
    title: str,
    message: str,
    link_url: str | None,
    lang: str,
    recipient_user_id: str,
) -> None:
    """Send the notification email via Resend in the background so a slow
    provider never stalls the caller. Bumps the dispatch counter on either
    outcome and swallows errors — an email failure must not block in-app
    delivery, which has already succeeded by the time we get here."""
    try:
        from app.services.email_service import EmailService  # late import, circular deps
        sent = await EmailService().send_notification_email(
            to_email=email,
            title=title,
            message=message,
            link_url=link_url,
            lang="en" if lang == "en" else "ar",  # Literal narrowing for mypy
            recipient_user_id=recipient_user_id,
        )
        _bump_dispatch("email", "ok" if sent else "fail")
    except Exception:
        _bump_dispatch("email", "fail")
        logger.debug("notification email dispatch failed", exc_info=True)


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


async def _resolve_email_context(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[str | None, bool]:
    """Return (email, email_notifications_enabled). Used by the optional email
    copy when a notification type is in the whitelist."""
    try:
        result = await db.execute(
            select(User.email, User.email_notifications_enabled).where(
                User.id == user_id
            )
        )
        row = result.first()
        if row is None:
            return None, False
        return row[0], bool(row[1])
    except Exception:
        logger.debug("email-context lookup failed", exc_info=True)
        return None, False


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

        # Optional email copy for a short whitelist of high-signal types.
        # Resolved inside a dedicated session in the background task so a
        # slow SMTP / Resend call can't stall the caller, and so a closed
        # request session doesn't block the send.
        if type in _EMAILABLE_TYPES:
            email, enabled = await _resolve_email_context(self.db, user_id)
            if email and enabled:
                link_url = _build_link_url(link_type, link_id)
                asyncio.create_task(
                    _send_notification_email_bg(
                        email=email,
                        title=title,
                        message=message,
                        link_url=link_url,
                        lang=locale if locale in _SUPPORTED_LOCALES else _DEFAULT_LOCALE,
                        recipient_user_id=str(user_id),
                    )
                )

        return notification

    async def get_notifications(
        self,
        user: User,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get notifications for a user. Archived rows are filtered out."""
        page_size = self.clamp_page_size(page_size)
        stmt = select(Notification).where(
            Notification.user_id == user.id,
            Notification.archived_at.is_(None),
        )

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
                Notification.archived_at.is_(None),
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
        """Get unread notification count (archived rows excluded)."""
        result = await self.db.execute(
            select(func.count()).where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
                Notification.archived_at.is_(None),
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
        """Mark all (non-archived) notifications as read."""
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
                Notification.archived_at.is_(None),
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
