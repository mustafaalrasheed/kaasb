"""
Kaasb Platform - Payment Schemas
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# === Payment Account ===

class PaymentAccountSetup(BaseModel):
    """Setup a payment account."""
    provider: str = Field(pattern=r"^(qi_card|stripe|wise)$")
    # Wise-specific
    wise_email: str | None = Field(None, max_length=255)
    wise_currency: str = Field(default="USD", max_length=3)
    # Qi Card-specific (optional — used for account label)
    qi_card_phone: str | None = Field(None, max_length=20, description="Iraqi phone number linked to Qi Card")


class PaymentAccountResponse(BaseModel):
    id: uuid.UUID
    provider: str
    status: str
    external_account_id: str | None = None
    wise_email: str | None = None
    wise_currency: str = "USD"
    qi_card_phone: str | None = None
    is_default: bool = True
    verified_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# === Fund Escrow (Client) ===

class EscrowFundRequest(BaseModel):
    """Client funds escrow for a milestone."""
    milestone_id: uuid.UUID
    payment_method_id: str | None = None  # Stripe payment method (legacy)
    # callback_url and return_url are server-controlled constants — never user-supplied


class EscrowFundResponse(BaseModel):
    escrow_id: uuid.UUID
    milestone_id: uuid.UUID
    amount: float
    platform_fee: float
    freelancer_amount: float
    status: str
    # Qi Card payment redirect
    payment_redirect_url: str | None = None  # Redirect client here to complete payment
    qi_card_payment_id: str | None = None
    # Legacy Stripe
    client_secret: str | None = None
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
    description: str | None = None
    external_transaction_id: str | None = None
    completed_at: datetime | None = None
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


# === Qi Card Webhook ===

class QiCardWebhookEvent(BaseModel):
    """Qi Card webhook payload sent to our callback URL after payment."""
    payment_id: str
    order_id: str  # This is our escrow order_id
    status: str    # "completed" | "failed" | "cancelled"
    amount: int    # Amount in IQD
    merchant_id: str
    signature: str | None = None  # HMAC-SHA256 signature for verification


# === Legacy Stripe Webhook (kept for compatibility) ===

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
