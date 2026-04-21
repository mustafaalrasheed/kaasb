"""
Kaasb Platform - Buyer Request Models
Fiverr-style "Post a Request": clients post briefs, freelancers send offers.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.models.base import BaseModel


class BuyerRequestStatus(str, enum.Enum):
    OPEN = "open"
    FILLED = "filled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class BuyerRequestOfferStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class BuyerRequest(BaseModel):
    """A short service request posted by a client. Freelancers browse and send offers."""

    __tablename__ = "buyer_requests"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    budget_min: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    budget_max: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BuyerRequestStatus] = mapped_column(
        Enum(BuyerRequestStatus, values_callable=lambda x: [e.value for e in x]),
        default=BuyerRequestStatus.OPEN,
        nullable=False,
        index=True,
    )
    # Auto-set to created_at + 7 days by the service layer
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    client: Mapped[User] = relationship("User", foreign_keys=[client_id])  # type: ignore[name-defined]
    category: Mapped[ServiceCategory | None] = relationship("ServiceCategory")  # type: ignore[name-defined]
    offers: Mapped[list[BuyerRequestOffer]] = relationship(
        "BuyerRequestOffer",
        back_populates="request",
        lazy="raise",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BuyerRequest '{self.title[:40]}' status={self.status.value}>"


class BuyerRequestOffer(BaseModel):
    """An offer sent by a freelancer in response to a BuyerRequest."""

    __tablename__ = "buyer_request_offers"

    request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buyer_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Optional: freelancer can link an existing service to this offer
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
    )
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[BuyerRequestOfferStatus] = mapped_column(
        Enum(BuyerRequestOfferStatus, values_callable=lambda x: [e.value for e in x]),
        default=BuyerRequestOfferStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Relationships
    request: Mapped[BuyerRequest] = relationship("BuyerRequest", back_populates="offers")
    freelancer: Mapped[User] = relationship("User", foreign_keys=[freelancer_id])  # type: ignore[name-defined]
    service: Mapped[Service | None] = relationship("Service")  # type: ignore[name-defined]

    # Legacy alias — old call sites use ``BuyerRequestOffer(gig_id=...)`` and ``offer.gig_id``.
    # TODO: remove once buyer_request_service.py sweep completes.
    gig_id = synonym("service_id")
    gig = synonym("service")

    def __repr__(self) -> str:
        return f"<BuyerRequestOffer freelancer={self.freelancer_id} status={self.status.value}>"
