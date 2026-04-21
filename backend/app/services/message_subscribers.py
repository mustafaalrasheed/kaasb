"""
Kaasb Platform - Message Event Subscribers

Wire chat domain events (``MessageSentEvent``) to their side-effects:
  * Create an in-app Notification for the recipient (except for support /
    system conversations, which use their own UX).
  * Push the message to the recipient over WebSocket.

Each subscriber runs in a background task with its OWN DB session — it
never shares the publisher's session, so a handler failure can't roll back
the user-facing write.
"""

from __future__ import annotations

import logging

from app.core.database import async_session
from app.models.message import ConversationType
from app.models.notification import NotificationType
from app.services.events import MessageSentEvent, bus
from app.services.notification_service import NotificationService
from app.services.websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)


async def _push_message_over_ws(event: MessageSentEvent) -> None:
    """Realtime push so the recipient's open chat updates without polling."""
    payload = {
        "type": "message",
        "data": {
            "conversation_id": str(event.conversation_id),
            "conversation_type": event.conversation_type.value,
            "id": str(event.message_id),
            "content": event.content,
            "sender_id": str(event.sender_id),
            "sender_name": event.sender_first_name,
            "sender_avatar": event.sender_avatar_url,
            "sender_role": event.sender_role.value,
            "is_system": event.is_system,
            "attachments": list(event.attachments or []),
            "created_at": event.created_at.isoformat(),
        },
    }
    await ws_manager.send_to_user(event.recipient_id, payload)


async def _create_notification_for_message(event: MessageSentEvent) -> None:
    """
    Insert an in-app notification for the message recipient.
    All conversation types notify the recipient, including SUPPORT so that
    admins get a bell when a user opens a support ticket.
    """
    if event.is_system:
        return

    if event.conversation_type == ConversationType.SUPPORT:
        title_ar = f"دعم — {event.sender_first_name}"[:100]
        title_en = f"Support — {event.sender_first_name}"[:100]
    else:
        title_ar = f"رسالة من {event.sender_first_name}"[:100]
        title_en = f"Message from {event.sender_first_name}"[:100]

    # The message body is the actual content typed by the sender, so the same
    # string is used regardless of the recipient's locale.
    body = event.content[:200]

    async with async_session() as db:
        try:
            svc = NotificationService(db)
            await svc.create_notification(
                user_id=event.recipient_id,
                type=NotificationType.NEW_MESSAGE,
                title_ar=title_ar,
                title_en=title_en,
                message_ar=body,
                message_en=body,
                link_type="message",
                link_id=event.conversation_id,
                actor_id=event.sender_id,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise


def register_message_subscribers() -> None:
    """Called once at app startup from main.py's lifespan."""
    bus.subscribe(MessageSentEvent, _push_message_over_ws)
    bus.subscribe(MessageSentEvent, _create_notification_for_message)
    logger.info("message subscribers registered (ws push + notification)")
