"""
Kaasb Platform - Buyer Request Schemas
Pydantic v2 request/response schemas for buyer requests and offers.
"""

import uuid  # noqa: I001
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.buyer_request import BuyerRequestOfferStatus, BuyerRequestStatus


# ──────────────────────────────────────────────
# Buyer Request
# ──────────────────────────────────────────────


class BuyerRequestCreate(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    description: str = Field(..., min_length=20, max_length=2000)
    category_id: Optional[uuid.UUID] = None
    budget_min: float = Field(..., gt=0)
    budget_max: float = Field(..., gt=0)
    delivery_days: int = Field(..., ge=1, le=90)

    model_config = ConfigDict(from_attributes=True)


class ClientBrief(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryBrief(BaseModel):
    id: uuid.UUID
    name_en: str
    name_ar: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class BuyerRequestOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    title: str
    description: str
    category_id: Optional[uuid.UUID] = None
    budget_min: float
    budget_max: float
    delivery_days: int
    status: BuyerRequestStatus
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    client: Optional[ClientBrief] = None
    category: Optional[CategoryBrief] = None
    offer_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BuyerRequestListOut(BaseModel):
    items: list[BuyerRequestOut]
    total: int
    page: int
    page_size: int


# ──────────────────────────────────────────────
# Buyer Request Offer
# ──────────────────────────────────────────────


class ServiceBrief(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    thumbnail_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


GigBrief = ServiceBrief


class FreelancerBrief(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None
    avg_rating: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class BuyerRequestOfferCreate(BaseModel):
    price: float = Field(..., gt=0)
    delivery_days: int = Field(..., ge=1, le=90)
    message: str = Field(..., min_length=20, max_length=1000)
    service_id: Optional[uuid.UUID] = Field(None, alias="gig_id")

    model_config = ConfigDict(populate_by_name=True)


class BuyerRequestOfferOut(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    freelancer_id: uuid.UUID
    service_id: Optional[uuid.UUID] = None
    price: float
    delivery_days: int
    message: str
    status: BuyerRequestOfferStatus
    created_at: datetime
    updated_at: datetime
    freelancer: Optional[FreelancerBrief] = None
    service: Optional[ServiceBrief] = None

    model_config = ConfigDict(from_attributes=True)
