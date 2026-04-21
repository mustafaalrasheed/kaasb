"""
Kaasb Platform - Payment Models
All payments go through Qi Card (Iraqi payment gateway).
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
    Integer,
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
    MANUAL = "manual"  # For admin-managed payouts
    QI_CARD = "qi_card"  # Iraqi Qi Card payment gateway


class PaymentAccountStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    SUSPENDED = "suspended"


class PaymentAccount(BaseModel):
    """User's Qi Card payment account for sending/receiving money."""

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
        Enum(PaymentProvider, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    status: Mapped[PaymentAccountStatus] = mapped_column(
        Enum(PaymentAccountStatus, values_callable=lambda x: [e.value for e in x]),
        default=PaymentAccountStatus.PENDING,
        nullable=False,
    )

    # Provider-specific IDs
    external_account_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

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
        Enum(TransactionType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, values_callable=lambda x: [e.value for e in x]),
        default=TransactionStatus.PENDING,
        nullable=False,
        index=True,
    )

    # === Financial ===
    amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="IQD", nullable=False)
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
        Enum(PaymentProvider, values_callable=lambda x: [e.value for e in x]),
        nullable=True
    )
    external_transaction_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )  # Qi Card payment reference

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
        # Uniqueness for active escrows is enforced by partial unique indexes
        # (uq_escrow_milestone_active, uq_escrow_gig_order_active) created in
        # migration l8g9h0i1j2k3.  Full UNIQUE constraints were removed to allow
        # retrying payment after a REFUNDED/FAILED escrow on the same milestone/order.
        CheckConstraint("amount > 0", name="ck_escrow_amount_positive"),
        CheckConstraint("platform_fee >= 0", name="ck_escrow_fee_non_negative"),
        CheckConstraint("freelancer_amount > 0", name="ck_escrow_freelancer_amount_positive"),
        CheckConstraint("freelancer_amount <= amount", name="ck_escrow_freelancer_le_total"),
        # Defence-in-depth: the release logic in PaymentService already refuses
        # to release a DISPUTED escrow, but a DB-level CHECK closes the window
        # where a future refactor accidentally paths around that service guard.
        # An escrow in DISPUTED state MUST NOT carry a release_transaction_id.
        CheckConstraint(
            "NOT (status = 'disputed' AND release_transaction_id IS NOT NULL)",
            name="ck_escrow_no_release_while_disputed",
        ),
    )

    # === Financial ===
    amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    platform_fee: Mapped[float] = mapped_column(Numeric(12, 4), default=0.0, nullable=False)
    freelancer_amount: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="IQD", nullable=False)

    # === Status ===
    status: Mapped[EscrowStatus] = mapped_column(
        Enum(EscrowStatus, values_callable=lambda x: [e.value for e in x]),
        default=EscrowStatus.PENDING,
        nullable=False,
        index=True,
    )

    # === Relations ===
    # contract_id / milestone_id used for contract-based escrow (proposals/contracts flow)
    # gig_order_id used for gig order escrow — exactly one of the two must be set
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="CASCADE"),
        nullable=True,
    )
    gig_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gig_orders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
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
    funded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # === Concurrency control ===
    # Incremented on every state-change UPDATE. PaymentService release/refund
    # paths include `WHERE version = :expected` so a stale-read UPDATE from a
    # racing coroutine refuses to commit. Defence-in-depth on top of SELECT
    # FOR UPDATE locking.
    version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )

    def __repr__(self) -> str:
        return f"<Escrow ${self.amount} ({self.status.value})>"
