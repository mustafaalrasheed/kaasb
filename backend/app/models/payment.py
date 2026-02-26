"""
Kaasb Platform - Payment Models
PaymentAccount, Transaction, and Escrow tables for the payment system.
Integrates with Stripe for payment processing.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Enum,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


# === Payment Account ===


class PaymentAccountStatus(str, enum.Enum):
    """Status of a user's payment account."""
    PENDING = "pending"       # Not yet verified
    ACTIVE = "active"         # Ready for transactions
    SUSPENDED = "suspended"   # Temporarily disabled
    CLOSED = "closed"         # Permanently closed


class PaymentAccount(BaseModel):
    """
    Payment account for each user.
    Freelancers have a Stripe Connect account for receiving payouts.
    Clients have a standard customer account for making payments.
    """

    __tablename__ = "payment_accounts"

    # === Owner ===
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user: Mapped["User"] = relationship("User", backref="payment_account", lazy="selectin")

    # === Stripe IDs ===
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    stripe_account_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )

    # === Status ===
    status: Mapped[PaymentAccountStatus] = mapped_column(
        Enum(PaymentAccountStatus),
        default=PaymentAccountStatus.PENDING,
        nullable=False,
        index=True,
    )

    # === Balances (in USD) ===
    available_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    pending_balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # === Payout Settings (freelancers) ===
    payout_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    charges_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # === Verification ===
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<PaymentAccount user={self.user_id} status={self.status.value}>"


# === Transaction ===


class TransactionType(str, enum.Enum):
    """Type of financial transaction."""
    DEPOSIT = "deposit"           # Client funds their account
    PAYMENT = "payment"           # Client pays into escrow
    RELEASE = "release"           # Escrow released to freelancer
    WITHDRAWAL = "withdrawal"     # Freelancer withdraws earnings
    REFUND = "refund"             # Refund back to client
    PLATFORM_FEE = "platform_fee" # Kaasb platform commission
    DISPUTE_HOLD = "dispute_hold" # Funds held during dispute


class TransactionStatus(str, enum.Enum):
    """Status of a transaction."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Transaction(BaseModel):
    """
    Record of every money movement on the platform.
    Immutable audit trail for all financial activity.
    """

    __tablename__ = "transactions"

    # === Parties ===
    from_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    from_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[from_user_id], backref="sent_transactions", lazy="selectin"
    )

    to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    to_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[to_user_id], backref="received_transactions", lazy="selectin"
    )

    # === Type & Status ===
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False, index=True
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        nullable=False,
        index=True,
    )

    # === Amount ===
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    net_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # === Stripe References ===
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, unique=True, index=True
    )
    stripe_transfer_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, unique=True, index=True
    )
    stripe_charge_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, index=True
    )

    # === Context ===
    contract_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contract: Mapped[Optional["Contract"]] = relationship(
        "Contract", backref="transactions", lazy="selectin"
    )

    milestone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    milestone: Mapped[Optional["Milestone"]] = relationship(
        "Milestone", backref="transactions", lazy="selectin"
    )

    # === Metadata ===
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_transactions_type_status", "type", "status"),
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.id} {self.type.value} ${self.amount}>"


# === Escrow ===


class EscrowStatus(str, enum.Enum):
    """Status of escrowed funds."""
    FUNDED = "funded"         # Client has paid, funds held
    RELEASED = "released"     # Funds released to freelancer
    REFUNDED = "refunded"     # Funds returned to client
    DISPUTED = "disputed"     # Funds frozen during dispute


class Escrow(BaseModel):
    """
    Escrow holds client funds securely until a milestone is approved.
    Funds are released to the freelancer upon client approval.
    """

    __tablename__ = "escrows"

    # === Parties ===
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client: Mapped["User"] = relationship(
        "User", foreign_keys=[client_id], backref="client_escrows", lazy="selectin"
    )

    freelancer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    freelancer: Mapped["User"] = relationship(
        "User", foreign_keys=[freelancer_id], backref="freelancer_escrows", lazy="selectin"
    )

    # === Context ===
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract: Mapped["Contract"] = relationship(
        "Contract", backref="escrows", lazy="selectin"
    )

    milestone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    milestone: Mapped[Optional["Milestone"]] = relationship(
        "Milestone", backref="escrow", lazy="selectin"
    )

    # === Financial ===
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    platform_fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # === Status ===
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus),
        default=EscrowStatus.FUNDED,
        nullable=False,
        index=True,
    )

    # === Stripe Reference ===
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, unique=True, index=True
    )

    # === Timestamps ===
    funded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refunded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Escrow {self.id} ${self.amount} ({self.status.value})>"
