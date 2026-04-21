"""
Kaasb Platform - Dispute Model (F5)
Dedicated dispute record with evidence files, admin assignment, and resolution trail.
The existing GigOrder.dispute_* fields remain for backward compatibility.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DisputeReason(str, enum.Enum):
    QUALITY = "quality"
    DEADLINE = "deadline"
    COMMUNICATION = "communication"
    NOT_AS_DESCRIBED = "not_as_described"
    OTHER = "other"


class DisputeStatus(str, enum.Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED_REFUND = "resolved_refund"
    RESOLVED_RELEASE = "resolved_release"
    CANCELLED = "cancelled"


class Dispute(BaseModel):
    """
    Formal dispute record associated with a ServiceOrder.
    One dispute per order (unique constraint on order_id).
    """

    __tablename__ = "disputes"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    initiated_by: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "client" | "freelancer"
    reason: Mapped[DisputeReason] = mapped_column(
        Enum(DisputeReason, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_files: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    status: Mapped[DisputeStatus] = mapped_column(
        Enum(DisputeStatus, values_callable=lambda x: [e.value for e in x]),
        default=DisputeStatus.OPEN,
        nullable=False,
        index=True,
    )

    # Admin assignment
    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    order: Mapped[ServiceOrder] = relationship("ServiceOrder")  # type: ignore[name-defined]
    admin: Mapped[User | None] = relationship("User", foreign_keys=[admin_id])  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Dispute order={self.order_id} status={self.status.value}>"
