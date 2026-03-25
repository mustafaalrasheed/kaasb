"""
Kaasb Platform - Message Service
Business logic for conversations and messaging.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException

from app.services.base import BaseService

from app.models.message import Conversation, Message
from app.models.user import User
from app.models.job import Job
from app.schemas.message import ConversationCreate, MessageCreate

logger = logging.getLogger(__name__)


class MessageService(BaseService):
    """Service for messaging operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def start_conversation(
        self, sender: User, data: ConversationCreate
    ) -> Conversation:
        """Start a new conversation or return existing one."""
        if sender.id == data.recipient_id:
            raise HTTPException(status_code=400, detail="Cannot message yourself")

        # Verify recipient exists
        result = await self.db.execute(
            select(User).where(User.id == data.recipient_id)
        )
        recipient = result.scalar_one_or_none()
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")

        # Normalize participant order (smaller UUID first for consistency)
        p1 = min(sender.id, data.recipient_id)
        p2 = max(sender.id, data.recipient_id)

        # Check for existing conversation
        stmt = select(Conversation).where(
            Conversation.participant_one_id == p1,
            Conversation.participant_two_id == p2,
        )
        if data.job_id:
            stmt = stmt.where(Conversation.job_id == data.job_id)
        else:
            stmt = stmt.where(Conversation.job_id.is_(None))

        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Send initial message in existing conversation
            await self._send_message(existing, sender, data.initial_message)
            return await self._get_conversation(existing.id)

        # Validate job if provided
        if data.job_id:
            job_result = await self.db.execute(
                select(Job).where(Job.id == data.job_id)
            )
            if not job_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Job not found")

        # Create conversation
        conversation = Conversation(
            participant_one_id=p1,
            participant_two_id=p2,
            job_id=data.job_id,
        )
        self.db.add(conversation)
        await self.db.flush()

        # Send initial message
        await self._send_message(conversation, sender, data.initial_message)

        return await self._get_conversation(conversation.id)

    async def send_message(
        self, sender: User, conversation_id: uuid.UUID, data: MessageCreate
    ) -> Message:
        """Send a message in an existing conversation."""
        conversation = await self._get_conversation(conversation_id)

        # Verify sender is a participant
        if sender.id not in (conversation.participant_one_id, conversation.participant_two_id):
            raise HTTPException(status_code=403, detail="Not part of this conversation")

        return await self._send_message(conversation, sender, data.content)

    async def _send_message(
        self, conversation: Conversation, sender: User, content: str
    ) -> Message:
        """Internal: create a message and update conversation."""
        message = Message(
            content=content,
            conversation_id=conversation.id,
            sender_id=sender.id,
        )
        self.db.add(message)

        # Atomically update conversation cache at the SQL level to prevent race conditions
        now = datetime.now(timezone.utc)
        update_values = {
            "last_message_text": content[:500],
            "last_message_at": now,
            "message_count": Conversation.message_count + 1,
        }
        # Increment unread for the OTHER participant
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
        await self.db.refresh(message, attribute_names=["sender"])
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
            )
            .where(
                or_(
                    Conversation.participant_one_id == user.id,
                    Conversation.participant_two_id == user.id,
                )
            )
        )

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Order by latest message
        stmt = stmt.order_by(Conversation.last_message_at.desc().nullslast())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        conversations = result.scalars().unique().all()

        # Enrich with other_user and unread
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
            raise HTTPException(status_code=403, detail="Not part of this conversation")

        # Mark as read for this user
        if user.id == conversation.participant_one_id:
            conversation.unread_one = 0
        else:
            conversation.unread_two = 0
        await self.db.flush()

        # Get messages
        stmt = (
            select(Message)
            .options(selectinload(Message.sender))
            .where(Message.conversation_id == conversation_id)
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Newest first
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
            )
            .where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
