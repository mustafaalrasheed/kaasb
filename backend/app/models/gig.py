"""
Kaasb Platform - Gig Models
Fiverr-style gig marketplace: freelancers post services, clients buy them.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class GigStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    PAUSED = "paused"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class GigOrderStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    REVISION_REQUESTED = "revision_requested"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class Category(BaseModel):
    """Top-level gig categories (e.g., Design, Programming, Writing)."""

    __tablename__ = "gig_categories"

    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    icon: Mapped[str | None] = mapped_column(String(50))  # lucide icon name
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    subcategories: Mapped[list["Subcategory"]] = relationship(
        "Subcategory", back_populates="category", lazy="raise"
    )
    gigs: Mapped[list["Gig"]] = relationship("Gig", back_populates="category", lazy="raise")


class Subcategory(BaseModel):
    """Subcategory under a Category."""

    __tablename__ = "gig_subcategories"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gig_categories.id", ondelete="CASCADE"), nullable=False
    )
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="subcategories")
    gigs: Mapped[list["Gig"]] = relationship("Gig", back_populates="subcategory", lazy="raise")


class Gig(BaseModel):
    """
    A service offered by a freelancer.
    Has up to 3 pricing packages (Basic, Standard, Premium).
    """

    __tablename__ = "gigs"

    # === Owner ===
    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # === Content ===
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)

    # === Category ===
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gig_categories.id", ondelete="SET NULL"), nullable=True
    )
    subcategory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gig_subcategories.id", ondelete="SET NULL"), nullable=True
    )

    # === Media ===
    # Stored as list of relative paths / CDN keys
    images: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))

    # === Status ===
    status: Mapped[GigStatus] = mapped_column(
        Enum(GigStatus, values_callable=lambda x: [e.value for e in x]),
        default=GigStatus.PENDING_REVIEW, nullable=False, index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # === Stats (denormalized for fast reads) ===
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)

    # === Relationships ===
    freelancer: Mapped["User"] = relationship("User", foreign_keys=[freelancer_id])  # type: ignore[name-defined]
    category: Mapped["Category | None"] = relationship("Category", back_populates="gigs")
    subcategory: Mapped["Subcategory | None"] = relationship("Subcategory", back_populates="gigs")
    packages: Mapped[list["GigPackage"]] = relationship(
        "GigPackage", back_populates="gig", cascade="all, delete-orphan", order_by="GigPackage.tier"
    )
    orders: Mapped[list["GigOrder"]] = relationship(
        "GigOrder", back_populates="gig", lazy="raise"
    )


class GigPackageTier(str, enum.Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class GigPackage(BaseModel):
    """
    One of three pricing tiers on a gig (Basic / Standard / Premium).
    """

    __tablename__ = "gig_packages"
    __table_args__ = (UniqueConstraint("gig_id", "tier", name="uq_gig_package_tier"),)

    gig_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gigs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tier: Mapped[GigPackageTier] = mapped_column(
        Enum(GigPackageTier, values_callable=lambda x: [e.value for e in x]), nullable=False
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)           # e.g. "Basic Package"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)    # IQD
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    revisions: Mapped[int] = mapped_column(Integer, default=1)              # -1 = unlimited
    features: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)

    # Relationships
    gig: Mapped["Gig"] = relationship("Gig", back_populates="packages")


class GigOrder(BaseModel):
    """
    An order placed by a client for a specific gig package.
    """

    __tablename__ = "gig_orders"

    gig_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gigs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gig_packages.id", ondelete="RESTRICT"), nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # === Order details ===
    status: Mapped[GigOrderStatus] = mapped_column(
        Enum(GigOrderStatus, values_callable=lambda x: [e.value for e in x]),
        default=GigOrderStatus.PENDING, nullable=False, index=True
    )
    requirements: Mapped[str | None] = mapped_column(Text)   # client's brief to freelancer
    price_paid: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    revisions_remaining: Mapped[int] = mapped_column(Integer, default=1)

    # === Dates ===
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # === Cancellation ===
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # === Relationships ===
    gig: Mapped["Gig"] = relationship("Gig", back_populates="orders")
    package: Mapped["GigPackage"] = relationship("GigPackage")
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id])  # type: ignore[name-defined]
    freelancer: Mapped["User"] = relationship("User", foreign_keys=[freelancer_id])  # type: ignore[name-defined]
