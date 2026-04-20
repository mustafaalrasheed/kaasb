"""
Kaasb Platform - Gig Schemas
Pydantic v2 request/response schemas for the gig marketplace.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.gig import GigOrderStatus, GigPackageTier, GigStatus

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
# Gig Package
# ──────────────────────────────────────────────

class GigPackageIn(BaseModel):
    tier: GigPackageTier
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


class GigPackageOut(GigPackageIn):
    id: uuid.UUID
    gig_id: uuid.UUID

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Requirement Questions / Answers (F3) — must be defined before GigCreate
# ──────────────────────────────────────────────

class RequirementQuestion(BaseModel):
    """One question in a gig's requirement template (F3)."""
    question: str = Field(..., min_length=3, max_length=300)
    type: str = Field(default="text", pattern="^(text|file|multiple_choice)$")
    required: bool = True
    options: list[str] = Field(default_factory=list)


class RequirementAnswer(BaseModel):
    """One client answer matching a RequirementQuestion (F3)."""
    question: str
    answer: str


# ──────────────────────────────────────────────
# Gig
# ──────────────────────────────────────────────

class GigCreate(BaseModel):
    title: str = Field(..., min_length=10, max_length=100)
    description: str = Field(..., min_length=50, max_length=5000)
    category_id: uuid.UUID
    subcategory_id: Optional[uuid.UUID] = None
    tags: list[str] = Field(default_factory=list, max_length=5)
    packages: list[GigPackageIn] = Field(..., min_length=1, max_length=3)
    requirement_questions: list[RequirementQuestion] = Field(default_factory=list, max_length=10)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip().lower() for t in v if t.strip()]
        if len(cleaned) > 5:
            raise ValueError("Maximum 5 tags allowed")
        return cleaned

    @model_validator(mode="after")
    def validate_packages(self) -> "GigCreate":
        tiers = [p.tier for p in self.packages]
        if len(set(tiers)) != len(tiers):
            raise ValueError("Each package tier (basic/standard/premium) must be unique")
        return self


class GigUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=10, max_length=100)
    description: Optional[str] = Field(None, min_length=50, max_length=5000)
    category_id: Optional[uuid.UUID] = None
    subcategory_id: Optional[uuid.UUID] = None
    tags: Optional[list[str]] = None
    packages: Optional[list[GigPackageIn]] = None
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


class GigOut(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    description: str
    tags: list[str] = []
    images: list[str] = []
    thumbnail_url: Optional[str] = None
    status: GigStatus
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
    packages: list[GigPackageOut] = []
    category: Optional[CategoryOut] = None

    model_config = {"from_attributes": True}


class GigListItem(BaseModel):
    """Lightweight gig representation for catalog/search listings."""
    id: uuid.UUID
    title: str
    slug: str
    thumbnail_url: Optional[str] = None
    avg_rating: float
    reviews_count: int
    orders_count: int
    min_price: Optional[float] = None   # cheapest package price
    delivery_days: Optional[int] = None  # fastest package delivery
    status: GigStatus
    freelancer: Optional[FreelancerBrief] = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Gig Order
# ──────────────────────────────────────────────

class GigOrderCreate(BaseModel):
    gig_id: uuid.UUID
    package_id: uuid.UUID
    requirements: Optional[str] = Field(None, max_length=2000)


class GigRequirementsSubmit(BaseModel):
    """Client submits structured answers to gig requirement questions (F3)."""
    answers: list[RequirementAnswer] = Field(..., min_length=1)


class DeliverBody(BaseModel):
    """Freelancer submits a delivery for an order (F4)."""
    message: str = Field(..., min_length=5, max_length=5000)
    files: list[str] = Field(default_factory=list)


class GigOrderUpdate(BaseModel):
    status: GigOrderStatus
    cancellation_reason: Optional[str] = Field(None, max_length=500)


class OrderDeliveryOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    message: str
    files: list[str] = []
    revision_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class GigOrderOut(BaseModel):
    id: uuid.UUID
    gig_id: uuid.UUID
    package_id: uuid.UUID
    client_id: uuid.UUID
    freelancer_id: uuid.UUID
    status: GigOrderStatus
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
    gig: Optional[GigOut] = None
    # Populated only on initial order placement when Qi Card payment is needed
    payment_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Pagination / Filters
# ──────────────────────────────────────────────

class GigSearchParams(BaseModel):
    q: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    subcategory_id: Optional[uuid.UUID] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    delivery_days: Optional[int] = None
    sort_by: str = "relevance"   # relevance | newest | rating | orders
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)
