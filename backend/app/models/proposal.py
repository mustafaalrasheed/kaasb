"""
Kaasb Platform - Proposal Model
Represents a freelancer's bid on a job posting.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ProposalStatus(str, enum.Enum):
    """Proposal lifecycle status."""
    PENDING = "pending"
    SHORTLISTED = "shortlisted"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Proposal(BaseModel):
    """
    Proposal model.
    A freelancer submits a proposal to bid on a job.
    One proposal per freelancer per job (enforced by unique constraint).
    """

    __tablename__ = "proposals"

    # Unique constraint: one proposal per freelancer per job
    __table_args__ = (
        UniqueConstraint("job_id", "freelancer_id", name="uq_proposal_job_freelancer"),
    )

    # === Bid Details ===
    cover_letter: Mapped[str] = mapped_column(Text, nullable=False)
    bid_amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    estimated_duration: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g., "2 weeks", "1 month"

    # === Status ===
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus),
        default=ProposalStatus.PENDING,
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
    # lazy="raise" prevents silent N+1 — use selectinload() in queries that need relations
    job: Mapped["Job"] = relationship(
        "Job", backref="proposals", lazy="raise"
    )

    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    freelancer: Mapped["User"] = relationship(
        "User", backref="proposals", lazy="raise"
    )

    # === Client response ===
    client_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === Timestamps ===
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Proposal {self.id} ({self.status.value}) on Job {self.job_id}>"
