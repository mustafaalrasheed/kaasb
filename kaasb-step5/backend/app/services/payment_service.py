"""
Kaasb Platform - Payment Service
Business logic for escrow, Stripe charges, Wise payouts, and platform fees.

Payment Flow:
1. Client funds escrow (Stripe charge → hold in escrow)
2. Freelancer works on milestone
3. Client approves milestone
4. Escrow releases → freelancer gets paid (Stripe/Wise minus platform fee)

Production Notes:
- Replace mock Stripe/Wise calls with real SDK calls
- Add webhook verification for Stripe
- Add idempotency keys for all financial operations
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.models.payment import (
    PaymentAccount, PaymentAccountStatus, PaymentProvider,
    Transaction, TransactionType, TransactionStatus,
    Escrow, EscrowStatus,
)
from app.models.contract import Contract, Milestone, MilestoneStatus
from app.models.user import User
from app.schemas.payment import (
    PaymentAccountSetup, EscrowFundRequest,
    EscrowFundResponse, EscrowReleaseResponse,
    PayoutRequest, PayoutResponse,
)

settings = get_settings()


class PaymentService:
    """Service for all payment operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.platform_fee_rate = settings.PLATFORM_FEE_PERCENT / 100.0

    # === Helpers ===

    def _calculate_fees(self, amount: float) -> dict:
        """Calculate platform fee and net amount."""
        platform_fee = round(amount * self.platform_fee_rate, 2)
        net_amount = round(amount - platform_fee, 2)
        return {
            "amount": amount,
            "platform_fee": platform_fee,
            "net_amount": net_amount,
        }

    async def _get_payment_account(
        self, user_id: uuid.UUID, provider: Optional[str] = None
    ) -> Optional[PaymentAccount]:
        """Get user's payment account."""
        stmt = select(PaymentAccount).where(
            PaymentAccount.user_id == user_id,
            PaymentAccount.status == PaymentAccountStatus.VERIFIED,
        )
        if provider:
            stmt = stmt.where(PaymentAccount.provider == PaymentProvider(provider))
        else:
            stmt = stmt.where(PaymentAccount.is_default == True)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # === Payment Account Management ===

    async def setup_payment_account(
        self, user: User, data: PaymentAccountSetup
    ) -> PaymentAccount:
        """Set up a payment account for a user."""
        # Check if already exists
        existing = await self.db.execute(
            select(PaymentAccount).where(
                PaymentAccount.user_id == user.id,
                PaymentAccount.provider == PaymentProvider(data.provider),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You already have a {data.provider} payment account",
            )

        provider = PaymentProvider(data.provider)

        if provider == PaymentProvider.STRIPE:
            # In production: call stripe.Customer.create()
            external_id = f"cus_mock_{uuid.uuid4().hex[:12]}"
        elif provider == PaymentProvider.WISE:
            if not data.wise_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Wise email is required for Wise accounts",
                )
            # In production: call Wise API to create recipient
            external_id = f"wise_mock_{uuid.uuid4().hex[:12]}"
        else:
            external_id = None

        account = PaymentAccount(
            user_id=user.id,
            provider=provider,
            status=PaymentAccountStatus.VERIFIED,  # Auto-verify in dev
            external_account_id=external_id,
            wise_email=data.wise_email if provider == PaymentProvider.WISE else None,
            wise_currency=data.wise_currency if provider == PaymentProvider.WISE else "USD",
            is_default=True,
            verified_at=datetime.now(timezone.utc),
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def get_payment_accounts(self, user: User) -> list[PaymentAccount]:
        """Get all payment accounts for user."""
        result = await self.db.execute(
            select(PaymentAccount)
            .where(PaymentAccount.user_id == user.id)
            .order_by(PaymentAccount.created_at.desc())
        )
        return list(result.scalars().all())

    # === Escrow: Fund ===

    async def fund_escrow(
        self, client: User, data: EscrowFundRequest
    ) -> EscrowFundResponse:
        """Client funds escrow for a milestone."""
        # Get milestone with contract
        result = await self.db.execute(
            select(Milestone).where(Milestone.id == data.milestone_id)
        )
        milestone = result.scalar_one_or_none()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        # Get contract
        result = await self.db.execute(
            select(Contract).where(Contract.id == milestone.contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Authorization
        if contract.client_id != client.id:
            raise HTTPException(status_code=403, detail="Only the client can fund escrow")

        # Check milestone is in a fundable state
        if milestone.status not in (MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot fund escrow for milestone with status '{milestone.status.value}'",
            )

        # Check not already funded
        existing = await self.db.execute(
            select(Escrow).where(
                Escrow.milestone_id == milestone.id,
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Escrow already funded for this milestone")

        # Calculate fees
        fees = self._calculate_fees(milestone.amount)

        # In production: Create Stripe PaymentIntent
        # stripe_intent = stripe.PaymentIntent.create(
        #     amount=int(milestone.amount * 100),  # cents
        #     currency="usd",
        #     customer=payment_account.external_account_id,
        #     payment_method=data.payment_method_id,
        #     confirm=True,
        #     metadata={"milestone_id": str(milestone.id)}
        # )
        mock_stripe_id = f"pi_mock_{uuid.uuid4().hex[:12]}"

        # Create transaction record
        transaction = Transaction(
            transaction_type=TransactionType.ESCROW_FUND,
            status=TransactionStatus.COMPLETED,
            amount=fees["amount"],
            currency="USD",
            platform_fee=0,  # Fee taken on release
            net_amount=fees["amount"],
            payer_id=client.id,
            contract_id=contract.id,
            milestone_id=milestone.id,
            provider=PaymentProvider.STRIPE,
            external_transaction_id=mock_stripe_id,
            description=f"Escrow funded for milestone: {milestone.title}",
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(transaction)
        await self.db.flush()

        # Create escrow
        escrow = Escrow(
            amount=fees["amount"],
            platform_fee=fees["platform_fee"],
            freelancer_amount=fees["net_amount"],
            currency="USD",
            status=EscrowStatus.FUNDED,
            contract_id=contract.id,
            milestone_id=milestone.id,
            client_id=client.id,
            freelancer_id=contract.freelancer_id,
            funding_transaction_id=transaction.id,
            funded_at=datetime.now(timezone.utc),
        )
        self.db.add(escrow)
        await self.db.flush()

        return EscrowFundResponse(
            escrow_id=escrow.id,
            milestone_id=milestone.id,
            amount=fees["amount"],
            platform_fee=fees["platform_fee"],
            freelancer_amount=fees["net_amount"],
            status="funded",
            client_secret=None,  # In production: stripe_intent.client_secret
            message=f"Escrow funded: ${fees['amount']:.2f} "
                    f"(freelancer gets ${fees['net_amount']:.2f} after {settings.PLATFORM_FEE_PERCENT}% fee)",
        )

    # === Escrow: Release (called when milestone approved) ===

    async def release_escrow(
        self, milestone_id: uuid.UUID
    ) -> Optional[EscrowReleaseResponse]:
        """Release escrow funds to freelancer after milestone approval."""
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.milestone_id == milestone_id,
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        escrow = result.scalar_one_or_none()
        if not escrow:
            return None  # No escrow to release (might be unfunded milestone)

        # Create platform fee transaction
        fee_tx = Transaction(
            transaction_type=TransactionType.PLATFORM_FEE,
            status=TransactionStatus.COMPLETED,
            amount=escrow.platform_fee,
            currency=escrow.currency,
            platform_fee=escrow.platform_fee,
            net_amount=0,
            payer_id=escrow.freelancer_id,
            contract_id=escrow.contract_id,
            milestone_id=milestone_id,
            description=f"Platform fee ({settings.PLATFORM_FEE_PERCENT}%)",
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(fee_tx)

        # Create release transaction
        release_tx = Transaction(
            transaction_type=TransactionType.ESCROW_RELEASE,
            status=TransactionStatus.COMPLETED,
            amount=escrow.freelancer_amount,
            currency=escrow.currency,
            platform_fee=0,
            net_amount=escrow.freelancer_amount,
            payer_id=escrow.client_id,
            payee_id=escrow.freelancer_id,
            contract_id=escrow.contract_id,
            milestone_id=milestone_id,
            provider=PaymentProvider.STRIPE,
            external_transaction_id=f"tr_mock_{uuid.uuid4().hex[:12]}",
            description=f"Milestone payment released",
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(release_tx)
        await self.db.flush()

        # Update escrow
        escrow.status = EscrowStatus.RELEASED
        escrow.released_at = datetime.now(timezone.utc)
        escrow.release_transaction_id = release_tx.id

        await self.db.flush()

        return EscrowReleaseResponse(
            escrow_id=escrow.id,
            milestone_id=milestone_id,
            amount=escrow.amount,
            freelancer_amount=escrow.freelancer_amount,
            status="released",
            message=f"${escrow.freelancer_amount:.2f} released to freelancer",
        )

    # === Escrow: Refund ===

    async def refund_escrow(
        self, milestone_id: uuid.UUID, reason: str = "Milestone cancelled"
    ) -> bool:
        """Refund escrow to client."""
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.milestone_id == milestone_id,
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        escrow = result.scalar_one_or_none()
        if not escrow:
            return False

        # In production: stripe.Refund.create()

        refund_tx = Transaction(
            transaction_type=TransactionType.ESCROW_REFUND,
            status=TransactionStatus.COMPLETED,
            amount=escrow.amount,
            currency=escrow.currency,
            platform_fee=0,
            net_amount=escrow.amount,
            payee_id=escrow.client_id,
            contract_id=escrow.contract_id,
            milestone_id=milestone_id,
            provider=PaymentProvider.STRIPE,
            external_transaction_id=f"re_mock_{uuid.uuid4().hex[:12]}",
            description=reason,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(refund_tx)

        escrow.status = EscrowStatus.REFUNDED
        escrow.released_at = datetime.now(timezone.utc)

        await self.db.flush()
        return True

    # === Payout: Freelancer withdraws funds ===

    async def request_payout(
        self, freelancer: User, data: PayoutRequest
    ) -> PayoutResponse:
        """Freelancer requests a payout to their payment account."""
        # Verify payment account
        result = await self.db.execute(
            select(PaymentAccount).where(
                PaymentAccount.id == data.payment_account_id,
                PaymentAccount.user_id == freelancer.id,
                PaymentAccount.status == PaymentAccountStatus.VERIFIED,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Payment account not found or not verified")

        # Check available balance (total released - total payouts)
        released = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.net_amount), 0.0)).where(
                Transaction.payee_id == freelancer.id,
                Transaction.transaction_type == TransactionType.ESCROW_RELEASE,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        total_released = released.scalar() or 0.0

        paid_out = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.payee_id == freelancer.id,
                Transaction.transaction_type == TransactionType.PAYOUT,
                Transaction.status.in_([TransactionStatus.COMPLETED, TransactionStatus.PROCESSING]),
            )
        )
        total_paid_out = paid_out.scalar() or 0.0

        available = total_released - total_paid_out
        if data.amount > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Available: ${available:.2f}",
            )

        # In production:
        # if account.provider == PaymentProvider.WISE:
        #     wise_transfer = wise_client.create_transfer(...)
        # elif account.provider == PaymentProvider.STRIPE:
        #     stripe.Transfer.create(...)

        payout_tx = Transaction(
            transaction_type=TransactionType.PAYOUT,
            status=TransactionStatus.PROCESSING,
            amount=data.amount,
            currency="USD",
            platform_fee=0,
            net_amount=data.amount,
            payee_id=freelancer.id,
            provider=account.provider,
            external_transaction_id=f"po_mock_{uuid.uuid4().hex[:12]}",
            description=f"Payout to {account.provider.value} account",
        )
        self.db.add(payout_tx)
        await self.db.flush()

        # In dev, auto-complete the payout
        payout_tx.status = TransactionStatus.COMPLETED
        payout_tx.completed_at = datetime.now(timezone.utc)
        await self.db.flush()

        return PayoutResponse(
            transaction_id=payout_tx.id,
            amount=data.amount,
            net_amount=data.amount,
            status="completed",
            provider=account.provider.value,
            message=f"${data.amount:.2f} payout processed via {account.provider.value}",
        )

    # === Transaction History ===

    async def get_transactions(
        self,
        user: User,
        transaction_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get transaction history for a user."""
        stmt = select(Transaction).where(
            (Transaction.payer_id == user.id) | (Transaction.payee_id == user.id)
        )

        if transaction_type:
            stmt = stmt.where(
                Transaction.transaction_type == TransactionType(transaction_type)
            )

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.order_by(Transaction.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        transactions = result.scalars().all()

        return {
            "transactions": list(transactions),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    # === Payment Summary ===

    async def get_payment_summary(self, user: User) -> dict:
        """Get payment summary for dashboard."""
        # Total earned (escrow releases where user is payee)
        earned_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.net_amount), 0.0)).where(
                Transaction.payee_id == user.id,
                Transaction.transaction_type == TransactionType.ESCROW_RELEASE,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        total_earned = earned_result.scalar() or 0.0

        # Total spent (escrow funds where user is payer)
        spent_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.payer_id == user.id,
                Transaction.transaction_type == TransactionType.ESCROW_FUND,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        total_spent = spent_result.scalar() or 0.0

        # Pending escrow (funded but not released)
        pending_result = await self.db.execute(
            select(func.coalesce(func.sum(Escrow.amount), 0.0)).where(
                (Escrow.client_id == user.id) | (Escrow.freelancer_id == user.id),
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        pending_escrow = pending_result.scalar() or 0.0

        # Platform fees paid
        fees_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.platform_fee), 0.0)).where(
                Transaction.payer_id == user.id,
                Transaction.transaction_type == TransactionType.PLATFORM_FEE,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        total_fees = fees_result.scalar() or 0.0

        # Transaction count
        count_result = await self.db.execute(
            select(func.count()).where(
                (Transaction.payer_id == user.id) | (Transaction.payee_id == user.id)
            )
        )
        tx_count = count_result.scalar() or 0

        # Payment accounts
        accounts = await self.get_payment_accounts(user)

        return {
            "total_earned": total_earned,
            "total_spent": total_spent,
            "pending_escrow": pending_escrow,
            "available_balance": total_earned,  # Simplified
            "total_platform_fees": total_fees,
            "transaction_count": tx_count,
            "payment_accounts": accounts,
        }
