"""
Kaasb Platform - In-process Domain Event Bus

Lightweight async pub/sub for decoupling services. Publishers emit events
with no knowledge of who consumes them; subscribers register once at startup.

Design choices:
  * In-process only. The event bus is per-worker — good enough for fanning
    out side-effects (notifications, analytics) of an already-persisted
    domain action. Cross-worker fanout is handled separately by the
    WebSocket manager's Redis pub/sub.
  * Handlers receive the event and create their OWN database session via
    the ``async_session`` factory. This guarantees the publisher's
    transaction is committed before handlers run (handlers are scheduled
    as background tasks) and prevents a failing handler from rolling back
    a successful domain operation.
  * Handlers are isolated from each other — a raised exception is logged
    and swallowed so one bad subscriber can't silently break the rest.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models.message import ConversationType, SenderRole

logger = logging.getLogger(__name__)


# === Event types ============================================================

@dataclass(frozen=True, slots=True)
class MessageSentEvent:
    """A message was successfully persisted in a conversation."""
    message_id: uuid.UUID
    conversation_id: uuid.UUID
    conversation_type: ConversationType
    sender_id: uuid.UUID
    sender_role: SenderRole
    sender_first_name: str
    sender_avatar_url: str | None
    recipient_id: uuid.UUID
    content: str
    is_system: bool
    attachments: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


Event = MessageSentEvent  # Union alias for when we add more event types.
Handler = Callable[[Any], Awaitable[None]]


# === Bus ====================================================================

class EventBus:
    """In-process async event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[type, list[Handler]] = {}

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)
        logger.info(
            "event bus: subscribed %s to %s",
            getattr(handler, "__qualname__", repr(handler)),
            event_type.__name__,
        )

    def publish(self, event: Any) -> None:
        """
        Fire-and-forget publish. Handlers run as background tasks so the
        caller's request/transaction is not blocked.

        Safe to call inside a transaction — handlers do not see the
        publisher's session.
        """
        handlers = self._subscribers.get(type(event), [])
        for handler in handlers:
            asyncio.create_task(self._invoke(handler, event))

    async def _invoke(self, handler: Handler, event: Any) -> None:
        try:
            await handler(event)
        except Exception:
            logger.exception(
                "event bus: handler %s failed for %s",
                getattr(handler, "__qualname__", repr(handler)),
                type(event).__name__,
            )

    def clear(self) -> None:
        """Test helper — drop all subscribers."""
        self._subscribers.clear()


# Module-level singleton.
bus = EventBus()
