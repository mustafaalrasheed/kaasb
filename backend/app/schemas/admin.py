"""
Kaasb Platform - Admin Schemas
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

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
    is_support: bool = False
    avg_rating: float
    total_reviews: int
    total_earnings: float
    jobs_completed: int
    is_online: bool
    last_login: datetime | None = None
    created_at: datetime
    # F6 chat moderation — surfaced so the admin UI can offer "Unsuspend Chat"
    # without a second round-trip and show running violation count for triage.
    chat_violations: int = 0
    chat_suspended_until: datetime | None = None

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    users: list[AdminUserInfo]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminUserStatusUpdate(BaseModel):
    # Constrained at the schema boundary so an invalid value surfaces as
    # 422 from Pydantic rather than as a raw 500 ValueError from
    # UserStatus(new_status) inside the service (nightly-2026-04-25 P1).
    status: Literal["active", "suspended", "deactivated"]


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
    # See AdminUserStatusUpdate — same rationale. JobStatus also has
    # in_progress / completed / cancelled values; admin moderation only
    # needs the three here (open is the default, closed shuts down a
    # fraudulent listing, cancelled is reserved if we ever need a softer
    # outcome than closed).
    status: Literal["open", "closed", "cancelled"]


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


class AdminEscrowFreelancerInfo(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    phone: str | None = None
    qi_card_phone: str | None = None
    qi_card_holder_name: str | None = None
    # Unique per-Qi-Card destination id. Required before release_escrow_by_id
    # lets the admin mark a payout; the admin types it into the Qi Card app.
    qi_card_account_number: str | None = None


class AdminEscrowInfo(BaseModel):
    escrow_id: uuid.UUID
    contract_id: Optional[uuid.UUID] = None
    gig_order_id: Optional[uuid.UUID] = None
    milestone_id: Optional[uuid.UUID] = None
    milestone_title: Optional[str] = None
    amount: float
    platform_fee: float
    freelancer_amount: float
    currency: str
    funded_at: datetime | None = None
    freelancer: AdminEscrowFreelancerInfo


class AdminProcessingPayoutInfo(BaseModel):
    """One PAYOUT transaction awaiting admin 'mark paid' after manual Qi Card transfer."""
    transaction_id: uuid.UUID
    amount: float
    currency: str
    requested_at: datetime
    provider: str | None = None
    description: str | None = None
    freelancer: AdminEscrowFreelancerInfo


class MarkPayoutPaidBody(BaseModel):
    """Optional admin note recorded in the audit log."""
    note: Optional[str] = None


class StuckPendingPayer(BaseModel):
    id: uuid.UUID
    username: str
    email: str


class StuckPendingTransactionInfo(BaseModel):
    """One PENDING transaction older than the reconciliation threshold.

    These require manual reconciliation against the Qi Card merchant
    dashboard until Kaasb wires up the v1 3DS status API.
    """
    transaction_id: uuid.UUID
    external_order_id: str | None = None
    amount: float
    currency: str
    transaction_type: str
    created_at: datetime
    age_minutes: int
    provider: str | None = None
    description: str | None = None
    payer: StuckPendingPayer | None = None


# === Payout Approval (Dual-Control) ===

class ReleaseRequestResult(BaseModel):
    """Result of an admin clicking 'Release' on a funded escrow."""
    status: str  # "released" | "pending_second_approval"
    escrow_id: uuid.UUID
    amount: float
    currency: str = "IQD"
    approval_id: Optional[uuid.UUID] = None  # set when pending_second_approval
    message: Optional[str] = None


class ReleaseRequestBody(BaseModel):
    """Optional note from the requesting admin."""
    note: Optional[str] = None


class PayoutApprovalDecision(BaseModel):
    note: Optional[str] = None


class PayoutApprovalInfo(BaseModel):
    id: uuid.UUID
    escrow_id: uuid.UUID
    amount: float
    currency: str
    status: str
    requested_by_id: Optional[uuid.UUID] = None
    requested_by_email: Optional[str] = None
    decided_by_id: Optional[uuid.UUID] = None
    decided_by_email: Optional[str] = None
    request_note: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    # Context for the admin reviewer — who's getting paid, how much, which order
    freelancer_id: Optional[uuid.UUID] = None
    freelancer_email: Optional[str] = None
    freelancer_username: Optional[str] = None
    gig_order_id: Optional[uuid.UUID] = None
    milestone_id: Optional[uuid.UUID] = None


class PayoutApprovalListResponse(BaseModel):
    approvals: list[PayoutApprovalInfo]
    total: int


class AdminAuditLogInfo(BaseModel):
    id: uuid.UUID
    admin_id: Optional[uuid.UUID] = None
    admin_email: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[uuid.UUID] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime


class AdminAuditLogListResponse(BaseModel):
    logs: list[AdminAuditLogInfo]
    total: int
    page: int
    page_size: int
