"""
Kaasb Platform - Contract & Milestone Schemas
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# === Embedded Info ===


class ContractUserInfo(BaseModel):
    """Minimal user info in contract responses."""
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ContractJobInfo(BaseModel):
    """Minimal job info in contract responses."""
    id: uuid.UUID
    title: str
    category: str
    job_type: str

    model_config = {"from_attributes": True}


# === Milestone Schemas ===


class MilestoneCreate(BaseModel):
    """Create a milestone on a contract."""
    title: str = Field(min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    amount: float = Field(ge=1, le=100000)
    due_date: Optional[datetime] = None
    order: int = Field(ge=0, le=100, default=0)


class MilestoneUpdate(BaseModel):
    """Update a pending milestone."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    amount: Optional[float] = Field(None, ge=1, le=100000)
    due_date: Optional[datetime] = None
    order: Optional[int] = Field(None, ge=0, le=100)


class MilestoneSubmit(BaseModel):
    """Freelancer submits a milestone for review."""
    submission_note: Optional[str] = Field(None, max_length=2000)


class MilestoneReview(BaseModel):
    """Client reviews a submitted milestone."""
    action: str = Field(pattern=r"^(approve|request_revision)$")
    feedback: Optional[str] = Field(None, max_length=2000)


class MilestoneDetail(BaseModel):
    """Full milestone response."""
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    amount: float
    order: int
    status: str
    due_date: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    submission_note: Optional[str] = None
    feedback: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# === Contract Schemas ===


class ContractCreate(BaseModel):
    """Client creates milestones when setting up a contract."""
    milestones: list[MilestoneCreate] = Field(min_length=1, max_length=20)


class ContractDetail(BaseModel):
    """Full contract response with milestones."""
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    total_amount: float
    amount_paid: float
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    created_at: datetime

    client: ContractUserInfo
    freelancer: ContractUserInfo
    job: ContractJobInfo
    milestones: list[MilestoneDetail] = []

    model_config = {"from_attributes": True}


class ContractSummary(BaseModel):
    """Contract card in listings."""
    id: uuid.UUID
    title: str
    total_amount: float
    amount_paid: float
    status: str
    started_at: datetime

    client: ContractUserInfo
    freelancer: ContractUserInfo
    job: ContractJobInfo

    milestone_count: int = 0
    completed_milestones: int = 0

    model_config = {"from_attributes": True}


class ContractListResponse(BaseModel):
    """Paginated contract list."""
    contracts: list[ContractSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
