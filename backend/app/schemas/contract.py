"""
Kaasb Platform - Contract & Milestone Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# === Embedded Info ===


class ContractUserInfo(BaseModel):
    """Minimal user info in contract responses."""
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    display_name: str | None = None
    avatar_url: str | None = None

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
    description: str | None = Field(None, max_length=2000)
    amount: float = Field(ge=1, le=100000)
    due_date: datetime | None = None
    order: int = Field(ge=0, le=100, default=0)


class MilestoneUpdate(BaseModel):
    """Update a pending milestone."""
    title: str | None = Field(None, min_length=3, max_length=200)
    description: str | None = Field(None, max_length=2000)
    amount: float | None = Field(None, ge=1, le=100000)
    due_date: datetime | None = None
    order: int | None = Field(None, ge=0, le=100)


class MilestoneSubmit(BaseModel):
    """Freelancer submits a milestone for review."""
    submission_note: str | None = Field(None, max_length=2000)


class MilestoneReview(BaseModel):
    """Client reviews a submitted milestone."""
    action: str = Field(pattern=r"^(approve|request_revision)$")
    feedback: str | None = Field(None, max_length=2000)


class MilestoneDetail(BaseModel):
    """Full milestone response."""
    id: uuid.UUID
    title: str
    description: str | None = None
    amount: float
    order: int
    status: str
    due_date: datetime | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    submission_note: str | None = None
    feedback: str | None = None
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
    description: str | None = None
    total_amount: float
    amount_paid: float
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    deadline: datetime | None = None
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
