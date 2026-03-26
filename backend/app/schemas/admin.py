"""
Kaasb Platform - Admin Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class PlatformStats(BaseModel):
    users: dict
    jobs: dict
    contracts: dict
    proposals: dict
    financials: dict
    reviews: dict
    messages: dict


class AdminUserInfo(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    first_name: str
    last_name: str
    primary_role: str
    status: str
    is_superuser: bool
    avg_rating: float
    total_reviews: int
    total_earnings: float
    jobs_completed: int
    is_online: bool
    last_login: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    users: list[AdminUserInfo]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminUserStatusUpdate(BaseModel):
    status: str  # active, suspended, deactivated


class AdminJobInfo(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    job_type: str
    budget_min: float | None = None
    budget_max: float | None = None
    category: str | None = None
    proposal_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminJobListResponse(BaseModel):
    jobs: list[AdminJobInfo]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminJobStatusUpdate(BaseModel):
    status: str  # open, closed, cancelled


class AdminTransactionInfo(BaseModel):
    id: uuid.UUID
    transaction_type: str
    status: str
    amount: float
    currency: str
    platform_fee: float
    net_amount: float
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminTransactionListResponse(BaseModel):
    transactions: list[AdminTransactionInfo]
    total: int
    page: int
    page_size: int
    total_pages: int
