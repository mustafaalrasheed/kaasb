"""
Kaasb Platform - Review Model
Both client and freelancer can leave reviews after a transaction completes.
Each party can only review the other once per transaction. A review is
attached to EITHER a contract (hourly/milestone work) OR a service order
(gig-style fixed-price), never both — enforced at the DB layer.
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Review(BaseModel):
    """
    Review model.
    After a contract OR service order is completed, each party can leave one
    review. Exactly one of ``contract_id`` / ``service_order_id`` is set.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
        CheckConstraint(
            "(contract_id IS NOT NULL AND service_order_id IS NULL) "
            "OR (contract_id IS NULL AND service_order_id IS NOT NULL)",
            name="ck_reviews_exactly_one_target",
        ),
        # Partial unique indexes replace the old NOT-NULL unique constraint:
        # each reviewer gets exactly one review per contract AND exactly one
        # per service order. Partial so NULLs on the unused side don't count.
        Index(
            "uq_reviews_contract_reviewer",
            "contract_id", "reviewer_id",
            unique=True,
            postgresql_where=(
                "contract_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_reviews_order_reviewer",
            "service_order_id", "reviewer_id",
            unique=True,
            postgresql_where=(
                "service_order_id IS NOT NULL"
            ),
        ),
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
    # Exactly one of contract_id / service_order_id is non-NULL (CHECK above).
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    contract: Mapped[Contract | None] = relationship(
        "Contract", backref="reviews", lazy="raise"
    )

    service_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_orders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    service_order: Mapped[ServiceOrder | None] = relationship(
        "ServiceOrder", backref="reviews", lazy="raise"
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
