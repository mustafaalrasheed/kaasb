"""
Kaasb Platform - Job Schemas
Pydantic models for job posting validation and responses.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# === Nested Client Info (embedded in job responses) ===


class JobClientInfo(BaseModel):
    """Minimal client info shown on job listings."""

    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    display_name: str | None = None
    avatar_url: str | None = None
    country: str | None = None
    total_spent: float = 0.0
    avg_rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# === Job Creation ===


class JobCreate(BaseModel):
    """Schema for creating a new job posting."""

    title: str = Field(min_length=10, max_length=200)
    description: str = Field(min_length=50, max_length=10000)
    category: str = Field(min_length=2, max_length=100)
    job_type: str = Field(pattern=r"^(fixed|hourly)$")

    # Pricing (conditional on job_type)
    budget_min: float | None = Field(None, ge=5)
    budget_max: float | None = Field(None, ge=5)
    fixed_price: float | None = Field(None, ge=5)

    # Requirements
    skills_required: list[str] | None = Field(None, max_length=15)
    experience_level: str | None = Field(
        None, pattern=r"^(entry|intermediate|expert)$"
    )
    duration: str | None = Field(
        None,
        pattern=r"^(less_than_1_week|1_to_4_weeks|1_to_3_months|3_to_6_months|more_than_6_months)$",
    )
    deadline: datetime | None = None

    @field_validator("fixed_price")
    @classmethod
    def validate_fixed_price(cls, v, info):
        data = info.data
        if data.get("job_type") == "fixed" and v is None:
            raise ValueError("Fixed price is required for fixed-price jobs")
        return v

    @field_validator("budget_min")
    @classmethod
    def validate_budget_min(cls, v, info):
        data = info.data
        if data.get("job_type") == "hourly" and v is None:
            raise ValueError("Minimum budget is required for hourly jobs")
        return v


class JobUpdate(BaseModel):
    """Schema for updating a job posting (client only, while still open/draft)."""

    title: str | None = Field(None, min_length=10, max_length=200)
    description: str | None = Field(None, min_length=50, max_length=10000)
    category: str | None = Field(None, min_length=2, max_length=100)
    job_type: str | None = Field(None, pattern=r"^(fixed|hourly)$")
    budget_min: float | None = Field(None, ge=5)
    budget_max: float | None = Field(None, ge=5)
    fixed_price: float | None = Field(None, ge=5)
    skills_required: list[str] | None = Field(None, max_length=15)
    experience_level: str | None = Field(
        None, pattern=r"^(entry|intermediate|expert)$"
    )
    duration: str | None = Field(
        None,
        pattern=r"^(less_than_1_week|1_to_4_weeks|1_to_3_months|3_to_6_months|more_than_6_months)$",
    )
    deadline: datetime | None = None


# === Job Responses ===


class JobSummary(BaseModel):
    """Job listing card — used in search results and browse pages."""

    id: uuid.UUID
    title: str
    category: str
    job_type: str
    budget_min: float | None = None
    budget_max: float | None = None
    fixed_price: float | None = None
    skills_required: list[str] | None = None
    experience_level: str | None = None
    duration: str | None = None
    status: str
    proposal_count: int = 0
    view_count: int = 0
    is_featured: bool = False
    created_at: datetime
    published_at: datetime | None = None

    # Embedded client info
    client: JobClientInfo

    model_config = {"from_attributes": True}

    @property
    def budget_display(self) -> str:
        if self.job_type == "fixed" and self.fixed_price:
            return f"${self.fixed_price:,.0f}"
        if self.budget_min and self.budget_max:
            return f"${self.budget_min:,.0f} - ${self.budget_max:,.0f}/hr"
        if self.budget_min:
            return f"From ${self.budget_min:,.0f}/hr"
        return "Budget not set"


class JobDetail(JobSummary):
    """Full job detail — used on the job detail page."""

    description: str
    deadline: datetime | None = None
    closed_at: datetime | None = None
    freelancer_id: uuid.UUID | None = None


class JobListResponse(BaseModel):
    """Paginated job listing response."""

    jobs: list[JobSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
