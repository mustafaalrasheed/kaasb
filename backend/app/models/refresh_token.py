"""
Kaasb Platform - Refresh Token Model
Stores issued refresh tokens for revocation support.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class RefreshToken(BaseModel):
    """Stored refresh tokens — enables logout and token revocation."""

    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)

    user: Mapped["User"] = relationship("User", backref="refresh_tokens", lazy="selectin")

    __table_args__ = (
        Index("ix_refresh_tokens_user_id_revoked", "user_id", "revoked"),
    )
