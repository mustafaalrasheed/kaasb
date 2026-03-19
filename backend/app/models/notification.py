"""
Kaasb Platform - Notification Model
In-app notifications for key platform events.
"""

import enum
import uuid
from typing import Optional

from sqlalchemy import (
    String,
    Enum,
    Text,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class NotificationType(str, enum.Enum):
    """Types of notifications."""
    # Proposals
    PROPOSAL_RECEIVED = "proposal_received"
    PROPOSAL_ACCEPTED = "proposal_accepted"
    PROPOSAL_REJECTED = "proposal_rejected"
    PROPOSAL_SHORTLISTED = "proposal_shortlisted"

    # Contracts
    CONTRACT_CREATED = "contract_created"
    CONTRACT_COMPLETED = "contract_completed"

    # Milestones
    MILESTONE_FUNDED = "milestone_funded"
    MILESTONE_SUBMITTED = "milestone_submitted"
    MILESTONE_APPROVED = "milestone_approved"
    MILESTONE_REVISION = "milestone_revision"

    # Payments
    PAYMENT_RECEIVED = "payment_received"
    PAYOUT_COMPLETED = "payout_completed"

    # Reviews
    REVIEW_RECEIVED = "review_received"

    # Messages
    NEW_MESSAGE = "new_message"

    # System
    SYSTEM_ALERT = "system_alert"


class Notification(BaseModel):
    """In-app notification for a user."""

    __tablename__ = "notifications"

    # === Content ===
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # === Status ===
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # === Target user ===
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], backref="notifications", lazy="selectin"
    )

    # === Optional link to related entity ===
    link_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # "contract", "job", "proposal", "message"
    link_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # === Sender (optional) ===
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Notification {self.type.value} for {self.user_id} read={self.is_read}>"
