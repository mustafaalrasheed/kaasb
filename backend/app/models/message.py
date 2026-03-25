"""
Kaasb Platform - Message Models
Conversations between users, optionally linked to a job or contract.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class Conversation(BaseModel):
    """
    Conversation between two users.
    Optionally linked to a job or contract for context.
    """

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "participant_one_id", "participant_two_id", "job_id",
            name="uq_conversation_participants_job",
        ),
    )

    # === Participants ===
    participant_one_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_one: Mapped["User"] = relationship(
        "User", foreign_keys=[participant_one_id], lazy="raise"
    )

    participant_two_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_two: Mapped["User"] = relationship(
        "User", foreign_keys=[participant_two_id], lazy="raise"
    )

    # === Context (optional) ===
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    job: Mapped[Optional["Job"]] = relationship("Job", lazy="raise")

    # === Last message cache for fast listing ===
    last_message_text: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # === Unread counts ===
    unread_one: Mapped[int] = mapped_column(Integer, default=0)  # Unread for participant_one
    unread_two: Mapped[int] = mapped_column(Integer, default=0)  # Unread for participant_two

    def __repr__(self) -> str:
        return f"<Conversation {self.id} ({self.message_count} msgs)>"

    def get_other_id(self, user_id: uuid.UUID) -> uuid.UUID:
        """Get the other participant's ID."""
        if user_id == self.participant_one_id:
            return self.participant_two_id
        return self.participant_one_id

    def get_unread_for(self, user_id: uuid.UUID) -> int:
        if user_id == self.participant_one_id:
            return self.unread_one
        return self.unread_two


class Message(BaseModel):
    """Individual message in a conversation."""

    __tablename__ = "messages"

    # === Content ===
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    # === Relationships ===
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", backref="messages_list", lazy="raise"
    )

    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped["User"] = relationship("User", lazy="raise")

    def __repr__(self) -> str:
        return f"<Message {self.id} from {self.sender_id}>"
