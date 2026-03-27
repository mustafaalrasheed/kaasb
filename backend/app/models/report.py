"""
Kaasb Platform - Report Model
Content moderation: users can report jobs, profiles, messages, and reviews.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ReportType(str, enum.Enum):
    JOB = "job"
    USER = "user"
    MESSAGE = "message"
    REVIEW = "review"


class ReportReason(str, enum.Enum):
    SPAM = "spam"
    FRAUD = "fraud"
    HARASSMENT = "harassment"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    FAKE_ACCOUNT = "fake_account"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Report(BaseModel):
    """
    Content moderation report.
    A user reports a job posting, another user, a message, or a review.
    Admins review and act on pending reports.
    """

    __tablename__ = "reports"

    # Who filed the report
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What was reported
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType), nullable=False, index=True
    )
    # UUID of the reported resource (job_id, user_id, message_id, review_id)
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Why it was reported
    reason: Mapped[ReportReason] = mapped_column(Enum(ReportReason), nullable=False)
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # optional free-text detail

    # Admin workflow
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        default=ReportStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Report {self.report_type.value}:{self.target_id} by {self.reporter_id} [{self.status.value}]>"
