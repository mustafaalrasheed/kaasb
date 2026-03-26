"""
Kaasb Platform - Payment Models
Supports hybrid payment: Stripe for global clients, Wise for Iraqi freelancer payouts.
Escrow holds funds during milestone work, releases on approval.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

# === Payment Account ===


class PaymentProvider(str, enum.Enum):
    """Supported payment providers."""
    STRIPE = "stripe"
    WISE = "wise"
    MANUAL = "manual"  # For admin-managed payouts
    QI_CARD = "qi_card"  # Iraqi Qi Card payment gateway


class PaymentAccountStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPENDED = "suspended"


class PaymentAccount(BaseModel):
    """
    User's payment account for receiving/sending money.
    - Clients: Stripe customer ID for charging cards
    - Freelancers: Wise recipient ID for payouts (or Stripe Connect)
    """

    __tablename__ = "payment_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user: Mapped["User"] = relationship(
        "User", backref="payment_accounts", lazy="raise"
    )

    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider), nullable=False
    )
    status: Mapped[PaymentAccountStatus] = mapped_column(
        Enum(PaymentAccountStatus),
        default=PaymentAccountStatus.PENDING,
        nullable=False,
    )

    # Provider-specific IDs
    external_account_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Stripe customer_id / Wise recipient_id

    # Wise-specific fields
    wise_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wise_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Qi Card-specific fields
    qi_card_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    qi_card_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Pending payment reference

    # Metadata (provider-specific data)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<PaymentAccount {self.provider.value} user={self.user_id}>"


# === Transaction ===


class TransactionType(str, enum.Enum):
    ESCROW_FUND = "escrow_fund"          # Client funds escrow
    ESCROW_RELEASE = "escrow_release"    # Escrow released to freelancer
    ESCROW_REFUND = "escrow_refund"      # Escrow refunded to client
    PLATFORM_FEE = "platform_fee"        # Platform takes fee
    PAYOUT = "payout"                    # Freelancer withdrawal


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Transaction(BaseModel):
    """
    Financial transaction record.
    Every money movement is recorded as a transaction.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
        CheckConstraint("platform_fee >= 0", name="ck_transaction_fee_non_negative"),
        CheckConstraint("net_amount > 0", name="ck_transaction_net_positive"),
    )

    # === Type & Status ===
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False, index=True
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
        index=True,
    )

    # === Financial ===
    amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    platform_fee: Mapped[float] = mapped_column(Numeric(12, 4), default=0.0, nullable=False)
    net_amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)

    # === Parties ===
    payer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[payer_id], lazy="raise"
    )

    payee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payee: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[payee_id], lazy="raise"
    )

    # === Related objects ===
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="SET NULL"),
        nullable=True,
    )

    # === Provider details ===
    provider: Mapped[PaymentProvider | None] = mapped_column(
        Enum(PaymentProvider), nullable=True
    )
    external_transaction_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )  # Stripe payment_intent / Wise transfer_id

    # === Notes ===
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === Timestamps ===
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_type.value} ${self.amount} ({self.status.value})>"


# === Escrow ===


class EscrowStatus(str, enum.Enum):
    PENDING = "pending"      # Awaiting payment confirmation (Qi Card redirect flow)
    FUNDED = "funded"        # Money held in escrow
    RELEASED = "released"    # Paid to freelancer
    REFUNDED = "refunded"    # Returned to client
    DISPUTED = "disputed"    # Under dispute


class Escrow(BaseModel):
    """
    Escrow holds funds for a milestone.
    Client funds escrow → freelancer works → client approves → escrow releases.
    """

    __tablename__ = "escrows"
    __table_args__ = (
        UniqueConstraint("milestone_id", name="uq_escrow_milestone"),
        CheckConstraint("amount > 0", name="ck_escrow_amount_positive"),
        CheckConstraint("platform_fee >= 0", name="ck_escrow_fee_non_negative"),
        CheckConstraint("freelancer_amount > 0", name="ck_escrow_freelancer_amount_positive"),
        CheckConstraint("freelancer_amount <= amount", name="ck_escrow_freelancer_le_total"),
    )

    # === Financial ===
    amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    platform_fee: Mapped[float] = mapped_column(Numeric(12, 4), default=0.0, nullable=False)
    freelancer_amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # === Status ===
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus),
        default=EscrowStatus.FUNDED,
        nullable=False,
        index=True,
    )

    # === Relations ===
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="CASCADE"),
        nullable=False,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # === Provider ===
    funding_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    release_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # === Timestamps ===
    funded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Escrow ${self.amount} ({self.status.value})>"
