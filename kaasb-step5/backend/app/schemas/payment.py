"""
Kaasb Platform - Payment Schemas
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# === Payment Account ===

class PaymentAccountSetup(BaseModel):
    """Setup a payment account."""
    provider: str = Field(pattern=r"^(stripe|wise)$")
    wise_email: Optional[str] = Field(None, max_length=255)
    wise_currency: str = Field(default="USD", max_length=3)


class PaymentAccountResponse(BaseModel):
    id: uuid.UUID
    provider: str
    status: str
    external_account_id: Optional[str] = None
    wise_email: Optional[str] = None
    wise_currency: str = "USD"
    is_default: bool = True
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# === Fund Escrow (Client) ===

class EscrowFundRequest(BaseModel):
    """Client funds escrow for a milestone."""
    milestone_id: uuid.UUID
    payment_method_id: Optional[str] = None  # Stripe payment method


class EscrowFundResponse(BaseModel):
    escrow_id: uuid.UUID
    milestone_id: uuid.UUID
    amount: float
    platform_fee: float
    freelancer_amount: float
    status: str
    client_secret: Optional[str] = None  # Stripe client_secret for frontend confirmation
    message: str

    model_config = {"from_attributes": True}


# === Release Escrow ===

class EscrowReleaseResponse(BaseModel):
    escrow_id: uuid.UUID
    milestone_id: uuid.UUID
    amount: float
    freelancer_amount: float
    status: str
    message: str


# === Transaction ===

class TransactionResponse(BaseModel):
    id: uuid.UUID
    transaction_type: str
    status: str
    amount: float
    currency: str
    platform_fee: float
    net_amount: float
    description: Optional[str] = None
    external_transaction_id: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# === Payment Dashboard Summary ===

class PaymentSummary(BaseModel):
    """User's payment overview."""
    total_earned: float = 0.0
    total_spent: float = 0.0
    pending_escrow: float = 0.0
    available_balance: float = 0.0
    total_platform_fees: float = 0.0
    transaction_count: int = 0
    payment_accounts: list[PaymentAccountResponse] = []


# === Webhook ===

class StripeWebhookEvent(BaseModel):
    """Stripe webhook payload (partial — we parse what we need)."""
    id: str
    type: str
    data: dict


# === Payout Request (Freelancer) ===

class PayoutRequest(BaseModel):
    """Freelancer requests a payout."""
    amount: float = Field(ge=10.0, le=50000.0)
    payment_account_id: uuid.UUID


class PayoutResponse(BaseModel):
    transaction_id: uuid.UUID
    amount: float
    net_amount: float
    status: str
    provider: str
    message: str
