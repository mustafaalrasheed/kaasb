"""
Kaasb Platform - Job Model
Represents job postings created by clients.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Boolean,
    Enum,
    Text,
    Float,
    Integer,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from app.models.base import BaseModel


class JobStatus(str, enum.Enum):
    """Job lifecycle status."""
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class JobType(str, enum.Enum):
    """Job pricing type."""
    FIXED = "fixed"
    HOURLY = "hourly"


class ExperienceLevel(str, enum.Enum):
    """Required experience level."""
    ENTRY = "entry"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class JobDuration(str, enum.Enum):
    """Expected job duration."""
    LESS_THAN_1_WEEK = "less_than_1_week"
    ONE_TO_4_WEEKS = "1_to_4_weeks"
    ONE_TO_3_MONTHS = "1_to_3_months"
    THREE_TO_6_MONTHS = "3_to_6_months"
    MORE_THAN_6_MONTHS = "more_than_6_months"


class Job(BaseModel):
    """
    Job posting model.
    Created by clients, visible to freelancers.
    """

    __tablename__ = "jobs"

    # === Core Fields ===
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # === Pricing ===
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType), nullable=False, default=JobType.FIXED
    )
    budget_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fixed_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # === Requirements ===
    skills_required: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String), nullable=True
    )
    experience_level: Mapped[Optional[ExperienceLevel]] = mapped_column(
        Enum(ExperienceLevel), nullable=True
    )
    duration: Mapped[Optional[JobDuration]] = mapped_column(
        Enum(JobDuration), nullable=True
    )

    # === Status & Visibility ===
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.OPEN, nullable=False, index=True
    )
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    # === Relationships ===
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # lazy="raise" prevents silent N+1 queries — use selectinload() in service queries
    client: Mapped["User"] = relationship(
        "User", foreign_keys=[client_id], backref="posted_jobs", lazy="raise"
    )

    # === Hired freelancer (set when contract starts) ===
    freelancer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # === Stats (denormalized) ===
    proposal_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)

    # === Timestamps ===
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Job {self.title[:40]} ({self.status.value})>"
