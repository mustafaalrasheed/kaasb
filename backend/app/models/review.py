"""
Kaasb Platform - Review Model
Both client and freelancer can leave reviews after a contract is completed.
Each party can only review the other once per contract.
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Review(BaseModel):
    """
    Review model.
    After a contract is completed, each party can leave one review.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint(
            "contract_id", "reviewer_id",
            name="uq_one_review_per_contract_per_user",
        ),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
    )

    # === Rating ===
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5 stars
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === Category ratings (optional, 1-5) ===
    communication_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    professionalism_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeliness_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # === Relationships ===
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract: Mapped[Contract] = relationship(
        "Contract", backref="reviews", lazy="raise"
    )

    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer: Mapped[User] = relationship(
        "User", foreign_keys=[reviewer_id], backref="reviews_given", lazy="raise"
    )

    reviewee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewee: Mapped[User] = relationship(
        "User", foreign_keys=[reviewee_id], backref="reviews_received", lazy="raise"
    )

    # === Metadata ===
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Review {self.rating}★ by {self.reviewer_id} for {self.reviewee_id}>"
