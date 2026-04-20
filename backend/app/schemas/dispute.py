"""
Kaasb Platform - Dispute Schemas (F5)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.dispute import DisputeReason, DisputeStatus


class DisputeCreate(BaseModel):
    reason: DisputeReason
    description: str = Field(..., min_length=30, max_length=3000)
    evidence_files: list[str] = Field(default_factory=list, max_length=10)


class DisputeAdminResolve(BaseModel):
    resolution: str = Field(..., pattern="^(release|refund)$")
    admin_notes: Optional[str] = Field(None, max_length=2000)


class DisputeAdminAssign(BaseModel):
    admin_notes: Optional[str] = Field(None, max_length=2000)


class OrderBrief(BaseModel):
    id: uuid.UUID
    status: str
    price_paid: float

    model_config = ConfigDict(from_attributes=True)


class UserBrief(BaseModel):
    id: uuid.UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DisputeOut(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    initiated_by: str
    reason: DisputeReason
    description: str
    evidence_files: list[str] = []
    status: DisputeStatus
    admin_id: Optional[uuid.UUID] = None
    admin_notes: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    admin: Optional[UserBrief] = None

    model_config = ConfigDict(from_attributes=True)
