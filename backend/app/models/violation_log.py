"""
Kaasb Platform - Violation Log Model (F6)
Tracks anti off-platform communication policy violations.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ViolationType(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    EXTERNAL_APP = "external_app"  # whatsapp, telegram, etc.


class ViolationAction(str, enum.Enum):
    WARNING = "warning"    # message delivered with contact info masked
    BLOCKED = "blocked"    # message not delivered
    SUSPENDED = "suspended"  # sender's chat access suspended 24h


class ViolationLog(BaseModel):
    """Records each policy violation for a message sender."""

    __tablename__ = "violation_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    violation_type: Mapped[ViolationType] = mapped_column(
        Enum(ViolationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    content_detected: Mapped[str] = mapped_column(String(500), nullable=False)
    action_taken: Mapped[ViolationAction] = mapped_column(
        Enum(ViolationAction, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<ViolationLog user={self.user_id} type={self.violation_type.value}>"
