"""
Kaasb Platform - Notification Model
In-app notifications for key platform events.
"""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # Services (renamed from gigs 2026-04-21 — see migration z2v3w4x5y6z7)
    SERVICE_APPROVED = "service_approved"
    SERVICE_REJECTED = "service_rejected"
    SERVICE_SUBMITTED = "service_submitted"
    SERVICE_NEEDS_REVISION = "service_needs_revision"
    # Legacy aliases — same underlying enum members as the SERVICE_* above.
    # Kept so existing callers (e.g. app.services.gig_service) compile until
    # their rename lands in the follow-up PR. Python treats repeated values
    # as aliases, so `NotificationType.GIG_APPROVED is NotificationType.SERVICE_APPROVED`.
    GIG_APPROVED = "service_approved"
    GIG_REJECTED = "service_rejected"
    GIG_SUBMITTED = "service_submitted"
    GIG_NEEDS_REVISION = "service_needs_revision"

    # Disputes
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_RESOLVED = "dispute_resolved"

    # Buyer Requests
    BUYER_REQUEST_OFFER_RECEIVED = "buyer_request_offer_received"
    BUYER_REQUEST_OFFER_ACCEPTED = "buyer_request_offer_accepted"
    BUYER_REQUEST_OFFER_REJECTED = "buyer_request_offer_rejected"

    # Order lifecycle (F3/F4)
    ORDER_REQUIREMENTS_SUBMITTED = "order_requirements_submitted"
    ORDER_DELIVERED = "order_delivered"
    ORDER_AUTO_COMPLETED = "order_auto_completed"

    # Seller levels (F2)
    SELLER_LEVEL_UPGRADED = "seller_level_upgraded"

    # Anti off-platform (F6)
    CHAT_VIOLATION_WARNING = "chat_violation_warning"

    # System
    SYSTEM_ALERT = "system_alert"


class Notification(BaseModel):
    """In-app notification for a user."""

    __tablename__ = "notifications"

    # === Content ===
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True,
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
        "User", foreign_keys=[user_id], backref="notifications", lazy="raise"
    )

    # === Optional link to related entity ===
    link_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # "contract", "job", "proposal", "message"
    link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # === Sender (optional) ===
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Notification {self.type.value} for {self.user_id} read={self.is_read}>"
