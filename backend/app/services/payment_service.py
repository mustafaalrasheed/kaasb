"""
Kaasb Platform - Payment Service
Business logic for escrow, Qi Card charges, and platform fees.

Payment Flow (Qi Card):
1. Client funds escrow → Qi Card payment initiated → redirect URL returned
2. Client completes payment on Qi Card → webhook confirms → escrow marked FUNDED
3. Freelancer works on milestone
4. Client approves milestone → escrow released → freelancer gets paid
5. Freelancer withdraws via Qi Card payout

Currency:
  - Internal amounts stored in USD (float)
  - Qi Card transactions converted to IQD at time of payment
"""

import logging
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.contract import Contract, Milestone, MilestoneStatus
from app.models.payment import (
    Escrow,
    EscrowStatus,
    PaymentAccount,
    PaymentAccountStatus,
    PaymentProvider,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.models.user import User
from app.schemas.payment import (
    EscrowFundRequest,
    EscrowFundResponse,
    EscrowReleaseResponse,
    PaymentAccountSetup,
    PayoutRequest,
    PayoutResponse,
)
from app.services.base import BaseService
from app.services.qi_card_client import QiCardClient, QiCardError, usd_to_iqd

logger = logging.getLogger(__name__)
settings = get_settings()


class PaymentService(BaseService):
    """Service for all payment operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.platform_fee_rate = Decimal(str(settings.PLATFORM_FEE_PERCENT)) / Decimal("100")
        self.qi_card = QiCardClient()

    # === Helpers ===

    def _calculate_fees(self, amount: float) -> dict:
        """Calculate platform fee and net amount using Decimal for precision."""
        amount_d = Decimal(str(amount))
        platform_fee = (amount_d * self.platform_fee_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        net_amount = (amount_d - platform_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "amount": float(amount_d),
            "platform_fee": float(platform_fee),
            "net_amount": float(net_amount),
        }

    async def _get_payment_account(
        self, user_id: uuid.UUID, provider: str | None = None
    ) -> PaymentAccount | None:
        """Get user's payment account."""
        stmt = select(PaymentAccount).where(
            PaymentAccount.user_id == user_id,
            PaymentAccount.status == PaymentAccountStatus.VERIFIED,
        )
        if provider:
            stmt = stmt.where(PaymentAccount.provider == PaymentProvider(provider))
        else:
            stmt = stmt.where(PaymentAccount.is_default.is_(True))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # === Payment Account Management ===

    async def setup_payment_account(
        self, user: User, data: PaymentAccountSetup
    ) -> PaymentAccount:
        """Set up a payment account for a user."""
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

        if provider == PaymentProvider.QI_CARD:
            external_id = f"qc_acct_{uuid.uuid4().hex[:12]}"
        elif provider == PaymentProvider.STRIPE:
            external_id = f"cus_mock_{uuid.uuid4().hex[:12]}"
        elif provider == PaymentProvider.WISE:
            if not data.wise_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Wise email is required for Wise accounts",
                )
            external_id = f"wise_mock_{uuid.uuid4().hex[:12]}"
        else:
            external_id = None

        account = PaymentAccount(
            user_id=user.id,
            provider=provider,
            status=PaymentAccountStatus.VERIFIED,
            external_account_id=external_id,
            wise_email=data.wise_email if provider == PaymentProvider.WISE else None,
            wise_currency=data.wise_currency if provider == PaymentProvider.WISE else "USD",
            qi_card_phone=data.qi_card_phone if provider == PaymentProvider.QI_CARD else None,
            is_default=True,
            verified_at=datetime.now(UTC),
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        logger.info("Payment account created: user=%s provider=%s", user.id, provider.value)
        return account

    async def get_payment_accounts(self, user: User) -> list[PaymentAccount]:
        """Get all payment accounts for user."""
        result = await self.db.execute(
            select(PaymentAccount)
            .where(PaymentAccount.user_id == user.id)
            .order_by(PaymentAccount.created_at.desc())
        )
        return list(result.scalars().all())

    # === Escrow: Fund via Qi Card ===

    async def fund_escrow(
        self, client: User, data: EscrowFundRequest
    ) -> EscrowFundResponse:
        """
        Client funds escrow for a milestone via Qi Card.

        Returns a redirect URL for the client to complete payment on Qi Card.
        Escrow is created in PENDING state and marked FUNDED via webhook.
        """
        # Use FOR UPDATE to prevent race conditions on concurrent escrow funding
        result = await self.db.execute(
            select(Milestone).where(Milestone.id == data.milestone_id).with_for_update()
        )
        milestone = result.scalar_one_or_none()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        result = await self.db.execute(
            select(Contract).where(Contract.id == milestone.contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        if contract.client_id != client.id:
            raise HTTPException(status_code=403, detail="Only the client can fund escrow")

        if milestone.status not in (MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot fund escrow for milestone with status '{milestone.status.value}'",
            )

        existing = await self.db.execute(
            select(Escrow).where(
                Escrow.milestone_id == milestone.id,
                Escrow.status.in_([EscrowStatus.FUNDED, EscrowStatus.PENDING]),
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Escrow already funded or pending for this milestone")

        fees = self._calculate_fees(milestone.amount)
        order_id = f"escrow-{milestone.id}"

        # Server-controlled redirect URLs — never user-supplied (SSRF protection)
        base = f"https://{settings.DOMAIN}"
        success_url = f"{base}/api/v1/payments/qi-card/success"
        failure_url = f"{base}/api/v1/payments/qi-card/failure"
        cancel_url  = f"{base}/api/v1/payments/qi-card/cancel"

        # Initiate Qi Card payment
        try:
            qi_result = await self.qi_card.create_payment(
                amount_usd=fees["amount"],
                order_id=order_id,
                success_url=success_url,
                failure_url=failure_url,
                cancel_url=cancel_url,
            )
        except QiCardError as e:
            logger.exception("Qi Card error in fund_escrow: %s", e)
            raise HTTPException(
                status_code=502,
                detail="Payment gateway error. Please try again later.",
            ) from e

        qi_payment_id = order_id   # Qi Card uses our orderId to identify the payment
        amount_iqd = qi_result["amount_iqd"]
        form_url = qi_result.get("link")

        # Create transaction and escrow atomically in a single flush
        transaction = Transaction(
            transaction_type=TransactionType.ESCROW_FUND,
            status=TransactionStatus.PENDING,
            amount=fees["amount"],
            currency=settings.QI_CARD_CURRENCY,
            platform_fee=0,
            net_amount=fees["amount"],
            payer_id=client.id,
            contract_id=contract.id,
            milestone_id=milestone.id,
            provider=PaymentProvider.QI_CARD,
            external_transaction_id=qi_payment_id,
            description=f"Qi Card escrow payment for milestone: {milestone.title}",
        )
        self.db.add(transaction)

        # Flush transaction first to get its ID for the escrow FK
        try:
            await self.db.flush()
        except (IntegrityError, SQLAlchemyError) as e:
            logger.exception("Database error creating transaction: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error") from e

        # Create escrow in PENDING state (will be FUNDED after webhook)
        escrow = Escrow(
            amount=fees["amount"],
            platform_fee=fees["platform_fee"],
            freelancer_amount=fees["net_amount"],
            currency=settings.QI_CARD_CURRENCY,
            status=EscrowStatus.PENDING,
            contract_id=contract.id,
            milestone_id=milestone.id,
            client_id=client.id,
            freelancer_id=contract.freelancer_id,
            funding_transaction_id=transaction.id,
            funded_at=None,  # Set only when webhook confirms actual payment
        )
        self.db.add(escrow)
        try:
            await self.db.flush()
        except IntegrityError as e:
            raise HTTPException(status_code=409, detail="Conflict: duplicate or constraint violation") from e
        except SQLAlchemyError as e:
            logger.exception("Database error in fund_escrow: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error") from e

        logger.info(
            "Qi Card payment initiated: milestone=%s payment_id=%s amount_usd=%s amount_iqd=%s",
            data.milestone_id, qi_payment_id, fees['amount'], amount_iqd,
        )

        return EscrowFundResponse(
            escrow_id=escrow.id,
            milestone_id=milestone.id,
            amount=fees["amount"],
            platform_fee=fees["platform_fee"],
            freelancer_amount=fees["net_amount"],
            status="pending_payment",
            payment_redirect_url=form_url,
            qi_card_payment_id=qi_payment_id,
            message=(
                f"Redirect client to complete Qi Card payment. "
                f"Amount: {amount_iqd:,} IQD (${fees['amount']:.2f}). "
                f"Freelancer receives ${fees['net_amount']:.2f} after "
                f"{settings.PLATFORM_FEE_PERCENT}% platform fee."
            ),
        )

    async def confirm_qi_card_payment(self, order_id: str) -> bool:
        """
        Called when Qi Card redirects the browser to successUrl?CartID=<order_id>.
        Marks the escrow as FUNDED and transaction as COMPLETED.
        order_id is our "escrow-<milestone_id>" string.
        """
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.external_transaction_id == order_id,
                Transaction.provider == PaymentProvider.QI_CARD,
                Transaction.transaction_type == TransactionType.ESCROW_FUND,
            )
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            logger.warning("Qi Card success: no transaction found for order_id=%s", order_id)
            return False

        if transaction.status == TransactionStatus.COMPLETED:
            logger.info("Qi Card webhook: already processed payment_id=%s", qi_payment_id)
            return True  # Idempotent

        # Update transaction
        transaction.status = TransactionStatus.COMPLETED
        transaction.completed_at = datetime.now(UTC)

        # Update escrow to FUNDED
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.funding_transaction_id == transaction.id,
            )
        )
        escrow = result.scalar_one_or_none()
        if escrow:
            escrow.status = EscrowStatus.FUNDED
            escrow.funded_at = datetime.now(UTC)

        try:
            await self.db.flush()
        except SQLAlchemyError as e:
            logger.exception("Database error confirming Qi Card payment: %s", e)
            return False

        logger.info(
            "Qi Card payment confirmed: order_id=%s transaction=%s escrow=%s",
            order_id, transaction.id, escrow.id if escrow else 'not found',
        )
        return True

    async def handle_qi_card_payment_failed(self, order_id: str) -> bool:
        """Mark transaction as FAILED when Qi Card redirects to failureUrl or cancelUrl."""
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.external_transaction_id == order_id,
                Transaction.provider == PaymentProvider.QI_CARD,
                Transaction.status == TransactionStatus.PENDING,
            )
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            return False

        transaction.status = TransactionStatus.FAILED
        transaction.failure_reason = "Payment cancelled or failed on Qi Card"

        # Cancel the escrow
        result = await self.db.execute(
            select(Escrow).where(Escrow.funding_transaction_id == transaction.id)
        )
        escrow = result.scalar_one_or_none()
        if escrow:
            escrow.status = EscrowStatus.REFUNDED  # Nothing was actually charged

        await self.db.flush()
        logger.info("Qi Card payment failed/cancelled: payment_id=%s", qi_payment_id)
        return True

    # === Escrow: Release (called when milestone approved) ===

    async def release_escrow(
        self, milestone_id: uuid.UUID
    ) -> EscrowReleaseResponse | None:
        """Release escrow funds to freelancer after milestone approval."""
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.milestone_id == milestone_id,
                Escrow.status == EscrowStatus.FUNDED,
            ).with_for_update()
        )
        escrow = result.scalar_one_or_none()
        if not escrow:
            return None

        # Platform fee transaction
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
            completed_at=datetime.now(UTC),
        )
        self.db.add(fee_tx)

        # Release transaction (internal ledger — real payout happens via request_payout)
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
            provider=PaymentProvider.QI_CARD,
            external_transaction_id=f"release_{uuid.uuid4().hex[:12]}",
            description="Milestone payment released to freelancer balance",
            completed_at=datetime.now(UTC),
        )
        self.db.add(release_tx)
        await self.db.flush()

        escrow.status = EscrowStatus.RELEASED
        escrow.released_at = datetime.now(UTC)
        escrow.release_transaction_id = release_tx.id

        try:
            await self.db.flush()
        except SQLAlchemyError as e:
            logger.exception("Database error in release_escrow: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error") from e

        logger.info("Escrow released: milestone=%s amount=%s", milestone_id, escrow.freelancer_amount)

        return EscrowReleaseResponse(
            escrow_id=escrow.id,
            milestone_id=milestone_id,
            amount=escrow.amount,
            freelancer_amount=escrow.freelancer_amount,
            status="released",
            message=f"${escrow.freelancer_amount:.2f} added to freelancer balance",
        )

    # === Escrow: Refund ===

    async def refund_escrow(
        self, milestone_id: uuid.UUID, reason: str = "Milestone cancelled"
    ) -> bool:
        """Refund escrow to client via Qi Card."""
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.milestone_id == milestone_id,
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        escrow = result.scalar_one_or_none()
        if not escrow:
            return False

        # Find original Qi Card payment_id
        original_tx = None
        if escrow.funding_transaction_id:
            tx_result = await self.db.execute(
                select(Transaction).where(Transaction.id == escrow.funding_transaction_id)
            )
            original_tx = tx_result.scalar_one_or_none()

        qi_payment_id = original_tx.external_transaction_id if original_tx else None
        amount_iqd = usd_to_iqd(escrow.amount)

        gateway_refund_succeeded = False
        if qi_payment_id:
            try:
                await self.qi_card.refund_payment(
                    payment_id=qi_payment_id,
                    amount_iqd=amount_iqd,
                    reason=reason,
                )
                gateway_refund_succeeded = True
            except QiCardError as e:
                logger.exception("Qi Card refund error: %s", e)
                # Record as PROCESSING so admin can resolve manually
        else:
            gateway_refund_succeeded = True  # No gateway call needed

        refund_tx = Transaction(
            transaction_type=TransactionType.ESCROW_REFUND,
            status=TransactionStatus.COMPLETED if gateway_refund_succeeded else TransactionStatus.PROCESSING,
            amount=escrow.amount,
            currency=escrow.currency,
            platform_fee=0,
            net_amount=escrow.amount,
            payee_id=escrow.client_id,
            contract_id=escrow.contract_id,
            milestone_id=milestone_id,
            provider=PaymentProvider.QI_CARD,
            external_transaction_id=f"refund_{uuid.uuid4().hex[:12]}",
            description=reason,
            completed_at=datetime.now(UTC),
        )
        self.db.add(refund_tx)

        escrow.status = EscrowStatus.REFUNDED
        escrow.released_at = datetime.now(UTC)

        await self.db.flush()
        logger.info("Escrow refunded: milestone=%s amount=%s", milestone_id, escrow.amount)
        return True

    # === Payout: Freelancer withdraws funds ===

    async def request_payout(
        self, freelancer: User, data: PayoutRequest
    ) -> PayoutResponse:
        """Freelancer requests a payout to their Qi Card account."""
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

        # Acquire advisory lock on user ID to prevent concurrent payout race conditions.
        # This ensures only one payout request per user is processed at a time.
        lock_key = int.from_bytes(freelancer.id.bytes[:8], byteorder="big") & 0x7FFFFFFFFFFFFFFF
        await self.db.execute(select(func.pg_advisory_xact_lock(lock_key)))

        # Check available balance (now safe under advisory lock)
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

        available = round(total_released - total_paid_out, 2)
        if data.amount > available:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Available: ${available:.2f}",
            )

        amount_iqd = usd_to_iqd(data.amount)

        # For Qi Card payouts: in production, call Qi Card payout/transfer API
        # Currently logged as processing — admin confirms manually until payout API is available
        payout_tx = Transaction(
            transaction_type=TransactionType.PAYOUT,
            status=TransactionStatus.PROCESSING,
            amount=data.amount,
            currency=settings.QI_CARD_CURRENCY,
            platform_fee=0,
            net_amount=data.amount,
            payee_id=freelancer.id,
            provider=account.provider,
            external_transaction_id=f"payout_{uuid.uuid4().hex[:12]}",
            description=(
                f"Qi Card payout: {amount_iqd:,} IQD (${data.amount:.2f}) "
                f"to phone {account.qi_card_phone or 'N/A'}"
            ),
        )
        self.db.add(payout_tx)
        await self.db.flush()

        # In sandbox/dev: auto-complete
        if settings.QI_CARD_SANDBOX or settings.ENVIRONMENT == "development":
            payout_tx.status = TransactionStatus.COMPLETED
            payout_tx.completed_at = datetime.now(UTC)

        try:
            await self.db.flush()
        except SQLAlchemyError as e:
            logger.exception("Database error in request_payout: %s", e)
            raise HTTPException(status_code=500, detail="Internal server error") from e

        logger.info(
            "Payout requested: freelancer=%s amount=%s (%s IQD) provider=%s",
            freelancer.id, data.amount, f"{amount_iqd:,}", account.provider.value,
        )

        payout_status = payout_tx.status.value
        return PayoutResponse(
            transaction_id=payout_tx.id,
            amount=data.amount,
            net_amount=data.amount,
            status=payout_status,
            provider=account.provider.value,
            message=(
                f"Payout of {amount_iqd:,} IQD (${data.amount:.2f}) "
                f"{'processed' if payout_status == 'completed' else 'queued for processing'} "
                f"via {account.provider.value}"
            ),
        )

    # === Transaction History ===

    async def get_transactions(
        self,
        user: User,
        transaction_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get transaction history for a user."""
        page_size = self.clamp_page_size(page_size)
        stmt = select(Transaction).where(
            (Transaction.payer_id == user.id) | (Transaction.payee_id == user.id)
        )

        if transaction_type:
            stmt = stmt.where(
                Transaction.transaction_type == TransactionType(transaction_type)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Transaction.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        transactions = result.scalars().all()

        return self.paginated_response(items=list(transactions), total=total, page=page, page_size=page_size, key="transactions")

    # === Payment Summary ===

    async def get_payment_summary(self, user: User) -> dict:
        """Get payment summary for dashboard."""
        earned_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.net_amount), 0.0)).where(
                Transaction.payee_id == user.id,
                Transaction.transaction_type == TransactionType.ESCROW_RELEASE,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        total_earned = earned_result.scalar() or 0.0

        spent_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.payer_id == user.id,
                Transaction.transaction_type == TransactionType.ESCROW_FUND,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        total_spent = spent_result.scalar() or 0.0

        pending_result = await self.db.execute(
            select(func.coalesce(func.sum(Escrow.amount), 0.0)).where(
                (Escrow.client_id == user.id) | (Escrow.freelancer_id == user.id),
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        pending_escrow = pending_result.scalar() or 0.0

        fees_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.platform_fee), 0.0)).where(
                Transaction.payer_id == user.id,
                Transaction.transaction_type == TransactionType.PLATFORM_FEE,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        total_fees = fees_result.scalar() or 0.0

        count_result = await self.db.execute(
            select(func.count()).where(
                (Transaction.payer_id == user.id) | (Transaction.payee_id == user.id)
            )
        )
        tx_count = count_result.scalar() or 0

        accounts = await self.get_payment_accounts(user)

        return {
            "total_earned": total_earned,
            "total_spent": total_spent,
            "pending_escrow": pending_escrow,
            "available_balance": total_earned,
            "total_platform_fees": total_fees,
            "transaction_count": tx_count,
            "payment_accounts": accounts,
        }
