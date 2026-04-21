"""
Kaasb Platform - Message Models
Conversations between users (and with admin/system), optionally linked
to a job or gig order.
"""

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ConversationType(str, enum.Enum):
    """
    Kind of conversation:
      * USER    — peer-to-peer between two platform users (job chats, pre-sale chats).
      * ORDER   — tied to a specific gig order (client ↔ freelancer about that order).
      * SUPPORT — user ↔ admin/support thread.
    """
    USER = "user"
    ORDER = "order"
    SUPPORT = "support"


class SenderRole(str, enum.Enum):
    """
    Role of the message sender at send time. Frozen on the message so that
    role changes on the user (e.g. primary_role flip, admin revoked) don't
    rewrite history. 'system' is used for server-generated events.
    """
    CLIENT = "client"
    FREELANCER = "freelancer"
    ADMIN = "admin"
    SYSTEM = "system"


class Conversation(BaseModel):
    """Conversation between two users or between a user and admin/support."""

    __tablename__ = "conversations"
    # Three partial unique indexes. Postgres treats NULLs as distinct in plain
    # unique constraints, which let concurrent start_conversation calls race
    # and create duplicate (p1, p2, NULL, NULL) rows. Partial indexes enforce
    # real uniqueness per conversation shape (bare / job-linked / order-linked).
    __table_args__ = (
        Index(
            "uq_conv_bare",
            "participant_one_id", "participant_two_id",
            unique=True,
            postgresql_where=text("job_id IS NULL AND order_id IS NULL"),
        ),
        Index(
            "uq_conv_by_job",
            "participant_one_id", "participant_two_id", "job_id",
            unique=True,
            postgresql_where=text("job_id IS NOT NULL"),
        ),
        Index(
            "uq_conv_by_order",
            "participant_one_id", "participant_two_id", "order_id",
            unique=True,
            postgresql_where=text("order_id IS NOT NULL"),
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

    # === Kind + context ===
    conversation_type: Mapped[ConversationType] = mapped_column(
        # values_callable so SQLAlchemy stores the enum ``.value`` (lowercase,
        # matching the PG enum type) rather than ``.name`` (UPPERCASE, which
        # the DB rejects with "invalid input value for enum conversationtype").
        Enum(
            ConversationType,
            name="conversationtype",
            values_callable=lambda e: [x.value for x in e],
        ),
        default=ConversationType.USER,
        nullable=False,
        index=True,
    )

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    job: Mapped[Optional["Job"]] = relationship("Job", lazy="raise")

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gig_orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order: Mapped[Optional["GigOrder"]] = relationship("GigOrder", lazy="raise")

    # === Last message cache for fast listing ===
    last_message_text: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    message_count: Mapped[int] = mapped_column(Integer, default=0)

    # === Unread counts ===
    unread_one: Mapped[int] = mapped_column(Integer, default=0)
    unread_two: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<Conversation {self.id} {self.conversation_type.value} ({self.message_count} msgs)>"

    def get_other_id(self, user_id: uuid.UUID) -> uuid.UUID:
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
    # Timestamp read by the recipient — powers ✓ vs ✓✓ UI. Null until read.
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Attachments: list of {url, filename, mime_type, size_bytes}.
    # Kept inline as JSONB rather than a separate table — messages are read
    # as a batch and the ratio of messages-with-attachments is low.
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False,
    )

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

    # Frozen role of sender at send time — see SenderRole docstring.
    sender_role: Mapped[SenderRole] = mapped_column(
        # Same values_callable rationale as ConversationType — DB enum values
        # are lowercase, so SQLAlchemy must bind ``.value`` not ``.name``.
        Enum(
            SenderRole,
            name="senderrole",
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} from {self.sender_id} ({self.sender_role.value})>"
