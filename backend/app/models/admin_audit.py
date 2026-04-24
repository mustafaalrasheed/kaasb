"""
Kaasb Platform - Admin Audit Log + Payout Approval Models

Append-only audit trail for admin actions and a two-admin approval queue
for payouts above a configurable IQD threshold (dual-control).

Audit log is written for EVERY admin-privileged action (escrow release,
user status change, promote/demote, dispute resolution, payout approval/reject)
so fraud or error can always be traced back to an admin + IP + timestamp.

Payout approvals are used only when the escrow amount exceeds
settings.PAYOUT_APPROVAL_THRESHOLD_IQD. A release below the threshold
is executed immediately by the single admin who requested it. Above the
threshold, a PayoutApproval row is created and a different admin must
click "Approve" before the release actually executes.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AdminAuditAction(str, enum.Enum):
    """Every kind of action that writes an admin audit log entry."""
    ESCROW_RELEASE_REQUESTED = "escrow_release_requested"
    ESCROW_RELEASED = "escrow_released"
    ESCROW_REFUNDED = "escrow_refunded"
    PAYOUT_APPROVED = "payout_approved"
    PAYOUT_REJECTED = "payout_rejected"
    PAYOUT_MARKED_PAID = "payout_marked_paid"
    USER_STATUS_CHANGED = "user_status_changed"
    JOB_STATUS_CHANGED = "job_status_changed"
    USER_PROMOTED_ADMIN = "user_promoted_admin"
    USER_DEMOTED_ADMIN = "user_demoted_admin"
    USER_PROMOTED_SUPPORT = "user_promoted_support"
    USER_DEMOTED_SUPPORT = "user_demoted_support"
    SERVICE_APPROVED = "service_approved"
    SERVICE_REJECTED = "service_rejected"
    DISPUTE_RESOLVED = "dispute_resolved"


class AdminAuditLog(BaseModel):
    """Append-only record of one admin action."""

    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        Index("ix_admin_audit_logs_admin_created", "admin_id", "created_at"),
        Index("ix_admin_audit_logs_target", "target_type", "target_id"),
    )

    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    admin: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "User", lazy="raise", foreign_keys=[admin_id]
    )

    action: Mapped[AdminAuditAction] = mapped_column(
        Enum(AdminAuditAction, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<AdminAuditLog {self.action.value} admin={self.admin_id}>"


class PayoutApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"   # Second admin approved; escrow released
    REJECTED = "rejected"   # Second admin rejected; escrow remains FUNDED
    CANCELLED = "cancelled" # Requester withdrew or escrow state changed


class PayoutApproval(BaseModel):
    """
    Dual-control approval for an escrow release above the IQD threshold.

    Flow:
      1. Admin A clicks "Release" on a FUNDED escrow. Amount > threshold →
         a PayoutApproval(status=PENDING) is created, NO money moves.
      2. Admin B (≠ A) sees it in the pending queue and clicks "Approve".
         → escrow is released, status=APPROVED.
      3. Or admin B clicks "Reject" with a reason → status=REJECTED, escrow
         stays FUNDED so admin A can try again or refund.
    """

    __tablename__ = "payout_approvals"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payout_approval_amount_positive"),
        Index("ix_payout_approvals_status", "status"),
    )

    escrow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("escrows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="IQD", nullable=False)

    status: Mapped[PayoutApprovalStatus] = mapped_column(
        Enum(PayoutApprovalStatus, values_callable=lambda x: [e.value for e in x]),
        default=PayoutApprovalStatus.PENDING,
        nullable=False,
        # Explicit Index in __table_args__ above handles this column. Setting
        # index=True here would cause Base.metadata.create_all() to emit a
        # duplicate "ix_payout_approvals_status" and break test setup.
    )

    request_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<PayoutApproval escrow={self.escrow_id} {self.status.value}>"
