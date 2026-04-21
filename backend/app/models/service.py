"""
Kaasb Platform - Service Models (خدمة / khidma)
Fiverr-style service marketplace: freelancers post services, clients buy them.

Renamed from "gig" to "service" to match Iraqi market terminology — the Arabic
UI already uses خدمة everywhere, this aligns the English side.
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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.models.base import BaseModel


class ServiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    NEEDS_REVISION = "needs_revision"
    ACTIVE = "active"
    PAUSED = "paused"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ServiceOrderStatus(str, enum.Enum):
    PENDING = "pending"
    PENDING_REQUIREMENTS = "pending_requirements"  # F3: awaiting client brief
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    REVISION_REQUESTED = "revision_requested"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class ServiceCategory(BaseModel):
    """Top-level service categories (e.g., Design, Programming, Writing)."""

    __tablename__ = "service_categories"

    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    icon: Mapped[str | None] = mapped_column(String(50))  # lucide icon name
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    subcategories: Mapped[list["ServiceSubcategory"]] = relationship(
        "ServiceSubcategory", back_populates="category", lazy="raise"
    )
    services: Mapped[list["Service"]] = relationship(
        "Service", back_populates="category", lazy="raise"
    )


class ServiceSubcategory(BaseModel):
    """Subcategory under a ServiceCategory."""

    __tablename__ = "service_subcategories"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    category: Mapped["ServiceCategory"] = relationship(
        "ServiceCategory", back_populates="subcategories"
    )
    services: Mapped[list["Service"]] = relationship(
        "Service", back_populates="subcategory", lazy="raise"
    )


class Service(BaseModel):
    """
    A service offered by a freelancer (خدمة).
    Has up to 3 pricing packages (Basic, Standard, Premium).
    """

    __tablename__ = "services"

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
        UUID(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    subcategory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_subcategories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # === Media ===
    # Stored as list of relative paths / CDN keys
    images: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))

    # === Status ===
    status: Mapped[ServiceStatus] = mapped_column(
        Enum(ServiceStatus, values_callable=lambda x: [e.value for e in x]),
        default=ServiceStatus.PENDING_REVIEW, nullable=False, index=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    revision_note: Mapped[str | None] = mapped_column(Text)  # feedback for needs_revision

    # === Review Audit Trail ===
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # === Requirement questions (F3) ===
    # JSON array: [{question, type, required, options}]
    requirement_questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # === Stats (denormalized for fast reads) ===
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)

    # === Rank score (F7) ===
    rank_score: Mapped[float] = mapped_column(Numeric(6, 2), default=0.0, nullable=False)
    rank_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # === Relationships ===
    freelancer: Mapped["User"] = relationship("User", foreign_keys=[freelancer_id])  # type: ignore[name-defined]
    category: Mapped["ServiceCategory | None"] = relationship(
        "ServiceCategory", back_populates="services"
    )
    subcategory: Mapped["ServiceSubcategory | None"] = relationship(
        "ServiceSubcategory", back_populates="services"
    )
    packages: Mapped[list["ServicePackage"]] = relationship(
        "ServicePackage",
        back_populates="service",
        cascade="all, delete-orphan",
        order_by="ServicePackage.tier",
    )
    orders: Mapped[list["ServiceOrder"]] = relationship(
        "ServiceOrder", back_populates="service", lazy="raise"
    )


class ServicePackageTier(str, enum.Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class ServicePackage(BaseModel):
    """
    One of three pricing tiers on a service (Basic / Standard / Premium).
    """

    __tablename__ = "service_packages"
    __table_args__ = (
        UniqueConstraint("service_id", "tier", name="uq_service_package_tier"),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tier: Mapped[ServicePackageTier] = mapped_column(
        Enum(ServicePackageTier, values_callable=lambda x: [e.value for e in x]), nullable=False
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)           # e.g. "Basic Package"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)    # IQD
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False)
    revisions: Mapped[int] = mapped_column(Integer, default=1)              # -1 = unlimited
    features: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)

    # Relationships
    service: Mapped["Service"] = relationship("Service", back_populates="packages")

    # Legacy alias — old call sites use ``ServicePackage(gig_id=...)`` kwargs.
    # TODO: remove once gig_service.py / buyer_request_service.py sweep completes.
    gig_id = synonym("service_id")


class ServiceOrder(BaseModel):
    """
    An order placed by a client for a specific service package.
    """

    __tablename__ = "service_orders"

    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_packages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # === Order details ===
    status: Mapped[ServiceOrderStatus] = mapped_column(
        Enum(ServiceOrderStatus, values_callable=lambda x: [e.value for e in x]),
        default=ServiceOrderStatus.PENDING, nullable=False, index=True
    )
    requirements: Mapped[str | None] = mapped_column(Text)   # legacy text brief
    # F3: structured requirement answers (JSONB)
    requirement_answers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    requirements_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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

    # === Dispute ===
    dispute_reason: Mapped[str | None] = mapped_column(Text)
    dispute_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispute_opened_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    dispute_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispute_resolution: Mapped[str | None] = mapped_column(String(50))

    # === Relationships ===
    service: Mapped["Service"] = relationship("Service", back_populates="orders")
    package: Mapped["ServicePackage"] = relationship("ServicePackage")
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id])  # type: ignore[name-defined]
    freelancer: Mapped["User"] = relationship("User", foreign_keys=[freelancer_id])  # type: ignore[name-defined]
    deliveries: Mapped[list["ServiceOrderDelivery"]] = relationship(
        "ServiceOrderDelivery",
        back_populates="order",
        lazy="raise",
        cascade="all, delete-orphan",
        order_by="ServiceOrderDelivery.revision_number",
    )

    # Legacy alias — old call sites use ``order.gig_id`` and ``ServiceOrder(gig_id=...)``.
    # TODO: remove once gig_service.py / payment_service.py sweep completes.
    gig_id = synonym("service_id")


class ServiceOrderDelivery(BaseModel):
    """A delivery submission by a freelancer on a service order (F4)."""

    __tablename__ = "service_order_deliveries"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    files: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    revision_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    order: Mapped["ServiceOrder"] = relationship("ServiceOrder", back_populates="deliveries")
