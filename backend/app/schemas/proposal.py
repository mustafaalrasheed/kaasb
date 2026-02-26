"""
Kaasb Platform - Proposal Schemas
Pydantic models for proposal validation and responses.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# === Nested Info (embedded in proposal responses) ===


class ProposalFreelancerInfo(BaseModel):
    """Minimal freelancer info shown on proposals."""

    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    title: Optional[str] = None
    hourly_rate: Optional[float] = None
    country: Optional[str] = None
    experience_level: Optional[str] = None
    skills: Optional[list[str]] = None
    avg_rating: float = 0.0
    total_reviews: int = 0
    jobs_completed: int = 0

    model_config = {"from_attributes": True}


class ProposalJobInfo(BaseModel):
    """Minimal job info shown on freelancer's proposals list."""

    id: uuid.UUID
    title: str
    category: str
    job_type: str
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    fixed_price: Optional[float] = None
    status: str

    model_config = {"from_attributes": True}


# === Create / Update ===


class ProposalCreate(BaseModel):
    """Schema for submitting a proposal."""

    cover_letter: str = Field(min_length=50, max_length=5000)
    bid_amount: float = Field(ge=5, le=100000)
    estimated_duration: Optional[str] = Field(None, max_length=50)


class ProposalUpdate(BaseModel):
    """Schema for freelancer updating their own proposal (while pending)."""

    cover_letter: Optional[str] = Field(None, min_length=50, max_length=5000)
    bid_amount: Optional[float] = Field(None, ge=5, le=100000)
    estimated_duration: Optional[str] = Field(None, max_length=50)


class ProposalRespond(BaseModel):
    """Schema for client responding to a proposal (shortlist/accept/reject)."""

    status: str = Field(pattern=r"^(shortlisted|accepted|rejected)$")
    client_note: Optional[str] = Field(None, max_length=2000)


# === Response Models ===


class ProposalDetail(BaseModel):
    """Full proposal detail — seen by the freelancer or the job's client."""

    id: uuid.UUID
    cover_letter: str
    bid_amount: float
    estimated_duration: Optional[str] = None
    status: str
    client_note: Optional[str] = None
    submitted_at: datetime
    responded_at: Optional[datetime] = None
    created_at: datetime

    # Embedded relations
    freelancer: ProposalFreelancerInfo
    job: ProposalJobInfo

    model_config = {"from_attributes": True}


class ProposalSummary(BaseModel):
    """Proposal card — used in listings."""

    id: uuid.UUID
    bid_amount: float
    estimated_duration: Optional[str] = None
    status: str
    submitted_at: datetime

    freelancer: ProposalFreelancerInfo
    job: ProposalJobInfo

    model_config = {"from_attributes": True}


class ProposalListResponse(BaseModel):
    """Paginated proposal list."""

    proposals: list[ProposalSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
