"""
Kaasb Platform - Message Service
Business logic for conversations and messaging.

The service owns persistence only. Side-effects (notifications, analytics,
realtime push) happen via domain events on ``app.services.events.bus`` so
the service stays decoupled from notification internals.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.models.gig import GigOrder
from app.models.job import Job
from app.models.message import Conversation, ConversationType, Message, SenderRole
from app.models.user import User, UserRole
from app.schemas.message import ConversationCreate, MessageCreate
from app.services.base import BaseService
from app.services.events import MessageSentEvent, bus

logger = logging.getLogger(__name__)


def _role_for(user: User) -> SenderRole:
    """Map a User's current standing to the SenderRole frozen on the message."""
    if user.is_superuser:
        return SenderRole.ADMIN
    if user.primary_role == UserRole.FREELANCER:
        return SenderRole.FREELANCER
    return SenderRole.CLIENT


class MessageService(BaseService):
    """Service for messaging operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def start_conversation(
        self, sender: User, data: ConversationCreate
    ) -> Conversation:
        """Start a new conversation or return existing one."""
        if sender.id == data.recipient_id:
            raise BadRequestError("Cannot message yourself")
        if data.job_id and data.order_id:
            raise BadRequestError("A conversation cannot be linked to both a job and an order")

        result = await self.db.execute(
            select(User).where(User.id == data.recipient_id)
        )
        recipient = result.scalar_one_or_none()
        if not recipient:
            raise NotFoundError("Recipient")

        # Normalize participant order (smaller UUID first for consistency)
        p1 = min(sender.id, data.recipient_id)
        p2 = max(sender.id, data.recipient_id)

        # Determine conversation type from context + participants.
        if data.order_id:
            conv_type = ConversationType.ORDER
        elif recipient.is_superuser or sender.is_superuser:
            conv_type = ConversationType.SUPPORT
        else:
            conv_type = ConversationType.USER

        # Check for existing conversation
        stmt = select(Conversation).where(
            Conversation.participant_one_id == p1,
            Conversation.participant_two_id == p2,
        )
        if data.job_id:
            stmt = stmt.where(Conversation.job_id == data.job_id)
        elif data.order_id:
            stmt = stmt.where(Conversation.order_id == data.order_id)
        else:
            stmt = stmt.where(Conversation.job_id.is_(None))
            stmt = stmt.where(Conversation.order_id.is_(None))

        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            await self._send_message(existing, sender, data.initial_message)
            return await self._get_conversation(existing.id)

        if data.job_id:
            job_result = await self.db.execute(
                select(Job).where(Job.id == data.job_id)
            )
            if not job_result.scalar_one_or_none():
                raise NotFoundError("Job")

        if data.order_id:
            order_result = await self.db.execute(
                select(GigOrder).where(GigOrder.id == data.order_id)
            )
            order = order_result.scalar_one_or_none()
            if not order:
                raise NotFoundError("Order")
            # Only the client or freelancer on the order may open/post to its chat.
            participants = {order.client_id, order.freelancer_id}
            if sender.id not in participants or data.recipient_id not in participants:
                raise ForbiddenError("Not a participant on this order")

        conversation = Conversation(
            participant_one_id=p1,
            participant_two_id=p2,
            conversation_type=conv_type,
            job_id=data.job_id,
            order_id=data.order_id,
        )
        self.db.add(conversation)
        await self.db.flush()

        await self._send_message(conversation, sender, data.initial_message)

        return await self._get_conversation(conversation.id)

    async def send_message(
        self, sender: User, conversation_id: uuid.UUID, data: MessageCreate
    ) -> Message:
        """Send a message in an existing conversation."""
        conversation = await self._get_conversation(conversation_id)

        if sender.id not in (conversation.participant_one_id, conversation.participant_two_id):
            raise ForbiddenError("Not part of this conversation")

        attachments = [a.model_dump() for a in data.attachments]
        return await self._send_message(
            conversation, sender, data.content, attachments=attachments,
        )

    async def send_system_message(
        self, conversation_id: uuid.UUID, content: str,
    ) -> Message:
        """
        Insert a server-generated message (e.g. 'Order delivered', 'Refund issued').
        The sender is the conversation's participant_one by convention — readers
        should check ``is_system`` / ``sender_role == system`` and render as a
        centered system notice rather than attributing to that user.
        """
        conversation = await self._get_conversation(conversation_id)

        message = Message(
            content=content,
            conversation_id=conversation.id,
            sender_id=conversation.participant_one_id,
            sender_role=SenderRole.SYSTEM,
            is_system=True,
            attachments=[],
        )
        self.db.add(message)

        now = datetime.now(UTC)
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation.id)
            .values(
                last_message_text=content[:500],
                last_message_at=now,
                message_count=Conversation.message_count + 1,
                unread_one=Conversation.unread_one + 1,
                unread_two=Conversation.unread_two + 1,
            )
        )

        await self.db.flush()
        # System messages bypass the notification subscriber — they're context, not an event.
        # They are still pushed via WS to both participants so open chats update in realtime.
        from app.services.websocket_manager import manager as ws_manager
        payload = _ws_payload_for(message, conversation, sender_first_name="", sender_avatar_url=None)
        asyncio.create_task(ws_manager.send_to_user(conversation.participant_one_id, payload))
        asyncio.create_task(ws_manager.send_to_user(conversation.participant_two_id, payload))

        return message

    async def _send_message(
        self,
        conversation: Conversation,
        sender: User,
        content: str,
        attachments: list[dict[str, Any]] | None = None,
    ) -> Message:
        """Internal: create a message, update conversation cache, publish event."""
        message = Message(
            content=content,
            conversation_id=conversation.id,
            sender_id=sender.id,
            sender_role=_role_for(sender),
            is_system=False,
            attachments=attachments or [],
        )
        self.db.add(message)

        # Atomically update conversation cache at the SQL level to prevent race conditions
        now = datetime.now(UTC)
        update_values: dict[str, Any] = {
            "last_message_text": content[:500],
            "last_message_at": now,
            "message_count": Conversation.message_count + 1,
        }
        if sender.id == conversation.participant_one_id:
            update_values["unread_two"] = Conversation.unread_two + 1
        else:
            update_values["unread_one"] = Conversation.unread_one + 1

        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation.id)
            .values(**update_values)
        )

        await self.db.flush()

        recipient_id = (
            conversation.participant_two_id
            if sender.id == conversation.participant_one_id
            else conversation.participant_one_id
        )

        # Publish domain event. Subscribers (notifications, analytics, WS
        # push) run as background tasks AFTER the request commits.
        bus.publish(MessageSentEvent(
            message_id=message.id,
            conversation_id=conversation.id,
            conversation_type=conversation.conversation_type,
            sender_id=sender.id,
            sender_role=message.sender_role,
            sender_first_name=sender.first_name,
            sender_avatar_url=sender.avatar_url,
            recipient_id=recipient_id,
            content=content,
            is_system=False,
            attachments=message.attachments,
            created_at=message.created_at,
        ))

        return message

    async def get_conversations(
        self,
        user: User,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all conversations for a user."""
        page_size = self.clamp_page_size(page_size)
        stmt = (
            select(Conversation)
            .options(
                selectinload(Conversation.participant_one),
                selectinload(Conversation.participant_two),
                selectinload(Conversation.job),
                selectinload(Conversation.order),
            )
            .where(
                or_(
                    Conversation.participant_one_id == user.id,
                    Conversation.participant_two_id == user.id,
                )
            )
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Conversation.last_message_at.desc().nullslast())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        conversations = result.scalars().unique().all()

        enriched = []
        for c in conversations:
            if user.id == c.participant_one_id:
                c._other_user = c.participant_two
                c._unread_count = c.unread_one
            else:
                c._other_user = c.participant_one
                c._unread_count = c.unread_two
            enriched.append(c)

        return self.paginated_response(items=enriched, total=total, page=page, page_size=page_size, key="conversations")

    async def get_messages(
        self,
        user: User,
        conversation_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """Get messages in a conversation. Marks messages as read."""
        page_size = self.clamp_page_size(page_size)
        conversation = await self._get_conversation(conversation_id)

        if user.id not in (conversation.participant_one_id, conversation.participant_two_id):
            raise ForbiddenError("Not part of this conversation")

        if user.id == conversation.participant_one_id:
            conversation.unread_one = 0
        else:
            conversation.unread_two = 0
        await self.db.flush()

        stmt = (
            select(Message)
            .options(selectinload(Message.sender))
            .where(Message.conversation_id == conversation_id)
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Message.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        messages = list(result.scalars().unique().all())

        return self.paginated_response(items=messages, total=total, page=page, page_size=page_size, key="messages")

    async def _get_conversation(self, conversation_id: uuid.UUID) -> Conversation:
        """Get conversation with participants loaded."""
        result = await self.db.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.participant_one),
                selectinload(Conversation.participant_two),
                selectinload(Conversation.job),
                selectinload(Conversation.order),
            )
            .where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise NotFoundError("Conversation")
        return conversation


def _ws_payload_for(
    message: Message,
    conversation: Conversation,
    sender_first_name: str,
    sender_avatar_url: str | None,
) -> dict[str, Any]:
    """Shared WS payload shape — kept in sync with notification subscriber."""
    return {
        "type": "message",
        "data": {
            "conversation_id": str(conversation.id),
            "conversation_type": conversation.conversation_type.value,
            "id": str(message.id),
            "content": message.content,
            "sender_id": str(message.sender_id),
            "sender_name": sender_first_name,
            "sender_avatar": sender_avatar_url,
            "sender_role": message.sender_role.value,
            "is_system": message.is_system,
            "attachments": list(message.attachments or []),
            "created_at": message.created_at.isoformat(),
        },
    }
