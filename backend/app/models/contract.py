"""
Kaasb Platform - Contract & Milestone Models
A Contract is created when a proposal is accepted.
Milestones break the contract into deliverable phases.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Enum,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


# === Contract ===


class ContractStatus(str, enum.Enum):
    """Contract lifecycle status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    PAUSED = "paused"


class Contract(BaseModel):
    """
    Contract model.
    Created automatically when a client accepts a freelancer's proposal.
    Links: client ↔ freelancer ↔ job ↔ proposal.
    """

    __tablename__ = "contracts"

    # === Contract Details ===
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # === Financial ===
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # === Status ===
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus),
        default=ContractStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # === Relationships ===
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job: Mapped["Job"] = relationship("Job", backref="contracts", lazy="selectin")

    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proposals.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    proposal: Mapped["Proposal"] = relationship(
        "Proposal", backref="contract", lazy="selectin"
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client: Mapped["User"] = relationship(
        "User", foreign_keys=[client_id], backref="client_contracts", lazy="selectin"
    )

    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    freelancer: Mapped["User"] = relationship(
        "User", foreign_keys=[freelancer_id], backref="freelancer_contracts", lazy="selectin"
    )

    # === Milestones relationship (loaded via backref from Milestone) ===

    # === Timestamps ===
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Contract {self.id} ({self.status.value})>"


# === Milestone ===


class MilestoneStatus(str, enum.Enum):
    """Milestone lifecycle status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    PAID = "paid"


class Milestone(BaseModel):
    """
    Milestone model.
    Breaks a contract into deliverable phases with individual amounts.
    """

    __tablename__ = "milestones"

    # === Details ===
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # === Financial ===
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    # === Status ===
    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus),
        default=MilestoneStatus.PENDING,
        nullable=False,
        index=True,
    )

    # === Relationship ===
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract: Mapped["Contract"] = relationship(
        "Contract", backref="milestones", lazy="selectin"
    )

    # === Timestamps ===
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # === Freelancer's submission note ===
    submission_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # === Client's feedback ===
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Milestone {self.id} #{self.order} ({self.status.value})>"
