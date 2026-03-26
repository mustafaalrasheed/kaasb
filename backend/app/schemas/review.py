"""
Kaasb Platform - Review Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    """Submit a review for the other party on a completed contract."""
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)
    communication_rating: int | None = Field(None, ge=1, le=5)
    quality_rating: int | None = Field(None, ge=1, le=5)
    professionalism_rating: int | None = Field(None, ge=1, le=5)
    timeliness_rating: int | None = Field(None, ge=1, le=5)


class ReviewUserInfo(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class ReviewContractInfo(BaseModel):
    id: uuid.UUID
    title: str

    model_config = {"from_attributes": True}


class ReviewDetail(BaseModel):
    id: uuid.UUID
    rating: int
    comment: str | None = None
    communication_rating: int | None = None
    quality_rating: int | None = None
    professionalism_rating: int | None = None
    timeliness_rating: int | None = None
    reviewer: ReviewUserInfo
    reviewee: ReviewUserInfo
    contract: ReviewContractInfo
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    reviews: list[ReviewDetail]
    total: int
    page: int
    page_size: int
    total_pages: int
    average_rating: float | None = None


class ReviewStats(BaseModel):
    """Aggregated review statistics for a user."""
    average_rating: float
    total_reviews: int
    rating_distribution: dict[str, int]  # {"5": 10, "4": 5, ...}
    avg_communication: float | None = None
    avg_quality: float | None = None
    avg_professionalism: float | None = None
    avg_timeliness: float | None = None
