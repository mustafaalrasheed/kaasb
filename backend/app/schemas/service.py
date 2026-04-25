"""
Kaasb Platform - Service Schemas (خدمة / khidma)
Pydantic v2 request/response schemas for the service marketplace.

Renamed from "gig" to "service" to match Iraqi market terminology.
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.service import ServiceOrderStatus, ServicePackageTier, ServiceStatus

# ──────────────────────────────────────────────
# Category
# ──────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: uuid.UUID
    name_en: str
    name_ar: str
    slug: str
    icon: Optional[str] = None
    sort_order: int

    model_config = {"from_attributes": True}


class SubcategoryOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    name_en: str
    name_ar: str
    slug: str

    model_config = {"from_attributes": True}


class CategoryWithSubsOut(CategoryOut):
    subcategories: list[SubcategoryOut] = []


# ──────────────────────────────────────────────
# Service Package
# ──────────────────────────────────────────────

class ServicePackageIn(BaseModel):
    tier: ServicePackageTier
    name: str = Field(..., min_length=3, max_length=80)
    description: str = Field(..., min_length=10, max_length=500)
    price: float = Field(..., gt=0)
    delivery_days: int = Field(..., ge=1, le=365)
    revisions: int = Field(default=1, ge=-1, le=99)  # -1 = unlimited
    features: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("price")
    @classmethod
    def price_min(cls, v: float) -> float:
        if v < 5000:  # Minimum 5,000 IQD (~$3.50)
            raise ValueError("Minimum package price is 5,000 IQD")
        return round(v, 2)


class ServicePackageOut(ServicePackageIn):
    id: uuid.UUID
    service_id: uuid.UUID

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Requirement Questions / Answers (F3) — must be defined before ServiceCreate
# ──────────────────────────────────────────────

class RequirementQuestion(BaseModel):
    """One question in a service's requirement template (F3)."""
    question: str = Field(..., min_length=3, max_length=300)
    type: str = Field(default="text", pattern="^(text|file|multiple_choice)$")
    required: bool = True
    options: list[str] = Field(default_factory=list)


class RequirementAnswer(BaseModel):
    """One client answer matching a RequirementQuestion (F3)."""
    question: str
    answer: str


# ──────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────

class ServiceCreate(BaseModel):
    title: str = Field(..., min_length=10, max_length=100)
    description: str = Field(..., min_length=50, max_length=5000)
    category_id: uuid.UUID
    subcategory_id: Optional[uuid.UUID] = None
    tags: list[str] = Field(default_factory=list, max_length=5)
    packages: list[ServicePackageIn] = Field(..., min_length=1, max_length=3)
    requirement_questions: list[RequirementQuestion] = Field(
        default_factory=list, max_length=10
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip().lower() for t in v if t.strip()]
        if len(cleaned) > 5:
            raise ValueError("Maximum 5 tags allowed")
        return cleaned

    @model_validator(mode="after")
    def validate_packages(self) -> "ServiceCreate":
        tiers = [p.tier for p in self.packages]
        if len(set(tiers)) != len(tiers):
            raise ValueError("Each package tier (basic/standard/premium) must be unique")
        return self


class ServiceUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=10, max_length=100)
    description: Optional[str] = Field(None, min_length=50, max_length=5000)
    category_id: Optional[uuid.UUID] = None
    subcategory_id: Optional[uuid.UUID] = None
    tags: Optional[list[str]] = None
    packages: Optional[list[ServicePackageIn]] = None
    requirement_questions: Optional[list[RequirementQuestion]] = None


class FreelancerBrief(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    avg_rating: Optional[float] = None
    seller_level: Optional[str] = None

    model_config = {"from_attributes": True}


class ServiceOut(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    description: str
    tags: list[str] = []
    images: list[str] = []
    thumbnail_url: Optional[str] = None
    status: ServiceStatus
    orders_count: int
    avg_rating: float
    reviews_count: int
    rank_score: float = 0.0
    category_id: Optional[uuid.UUID] = None
    subcategory_id: Optional[uuid.UUID] = None
    revision_note: Optional[str] = None
    requirement_questions: Optional[list] = None
    created_at: datetime
    updated_at: datetime
    freelancer: Optional[FreelancerBrief] = None
    packages: list[ServicePackageOut] = []
    category: Optional[CategoryOut] = None

    model_config = {"from_attributes": True}


class ServiceListItem(BaseModel):
    """Lightweight service representation for catalog/search listings."""
    id: uuid.UUID
    title: str
    slug: str
    thumbnail_url: Optional[str] = None
    avg_rating: float
    reviews_count: int
    orders_count: int
    min_price: Optional[float] = None   # cheapest package price
    delivery_days: Optional[int] = None  # fastest package delivery
    status: ServiceStatus
    freelancer: Optional[FreelancerBrief] = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Service Order
# ──────────────────────────────────────────────

class ServiceOrderCreate(BaseModel):
    service_id: uuid.UUID
    package_id: uuid.UUID
    requirements: Optional[str] = Field(None, max_length=2000)
    # Payment gateway. Defaults to qi_card for backwards compatibility with
    # existing buyers' bookmarked checkout flows; clients pass "zain_cash"
    # when the buyer picked it on the choice screen.
    provider: Literal["qi_card", "zain_cash"] = "qi_card"


class ServiceRequirementsSubmit(BaseModel):
    """Client submits structured answers to service requirement questions (F3)."""
    answers: list[RequirementAnswer] = Field(..., min_length=1)


class DeliverBody(BaseModel):
    """Freelancer submits a delivery for an order (F4)."""
    message: str = Field(..., min_length=5, max_length=5000)
    files: list[str] = Field(default_factory=list)


class ServiceOrderUpdate(BaseModel):
    status: ServiceOrderStatus
    cancellation_reason: Optional[str] = Field(None, max_length=500)


class OrderDeliveryOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    message: str
    files: list[str] = []
    revision_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceOrderOut(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    package_id: uuid.UUID
    client_id: uuid.UUID
    freelancer_id: uuid.UUID
    status: ServiceOrderStatus
    requirements: Optional[str] = None
    requirement_answers: Optional[list] = None
    requirements_submitted_at: Optional[datetime] = None
    price_paid: float
    delivery_days: int
    revisions_remaining: int
    due_date: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    service: Optional[ServiceOut] = None
    # Populated only on initial order placement when Qi Card payment is needed
    payment_url: Optional[str] = None
    # Populated on list endpoints — whether the calling user has already
    # submitted a review on this completed order. Null on detail endpoints
    # (stays None when not computed). Drives the "Leave review" CTA visibility.
    has_reviewed: Optional[bool] = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Pagination / Filters
# ──────────────────────────────────────────────

class ServiceSearchParams(BaseModel):
    q: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    subcategory_id: Optional[uuid.UUID] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    delivery_days: Optional[int] = None
    sort_by: str = "relevance"   # relevance | newest | rating | orders
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)
