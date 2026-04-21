"""
Kaasb Platform - Payment Service
Business logic for escrow, Qi Card charges, and platform fees.

Payment Flow:
1. Client funds escrow → Qi Card payment initiated → redirect URL returned
2. Client completes payment on Qi Card → webhook confirms → escrow marked FUNDED
3. Freelancer works on milestone
4. Client approves milestone → escrow released → freelancer gets paid
5. Freelancer withdraws via Qi Card payout

Currency:
  - Amounts stored as USD floats internally
  - Converted to IQD at time of Qi Card transaction
"""

import hashlib
import hmac as _hmac
import logging
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, ExternalServiceError, ForbiddenError, NotFoundError
from app.models.contract import Contract, Milestone, MilestoneStatus
from app.models.notification import NotificationType
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
from app.models.service import ServiceOrder, ServiceOrderStatus
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
from app.services.notification_service import notify
from app.services.qi_card_client import QiCardClient, QiCardError

logger = logging.getLogger(__name__)
settings = get_settings()


def _record_escrow_transition(from_status: str, to_status: str) -> None:
    """Emit the Prometheus transition counter. Isolated in a helper so service
    call-sites stay readable and so the import doesn't fire at module load
    time (the middleware package is only imported when FastAPI boots)."""
    try:
        from app.middleware.monitoring import ESCROW_STATE_TRANSITIONS
        ESCROW_STATE_TRANSITIONS.labels(from_status=from_status, to_status=to_status).inc()
    except Exception:
        # Metrics must never block the money-state transition they observe.
        logger.debug("metrics: escrow transition emit failed", exc_info=True)


class PaymentService(BaseService):
    """Service for all payment operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)
        self.platform_fee_rate = Decimal(str(settings.PLATFORM_FEE_PERCENT)) / Decimal("100")
        self.qi_card = QiCardClient()

    # === Helpers ===

    def _sign_order_id(self, order_id: str) -> str:
        """HMAC-SHA256 signature for Qi Card success/failure redirect URLs.
        Prevents unauthenticated users from faking payment confirmation by
        directly hitting the success URL with a known order_id.
        """
        return _hmac.new(
            settings.SECRET_KEY.encode(),
            order_id.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _verify_order_sig(self, order_id: str, sig: str) -> bool:
        """Constant-time verify of the HMAC signature included in the success URL."""
        if not sig:
            return False
        expected = self._sign_order_id(order_id)
        return _hmac.compare_digest(expected, sig)

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
        """
        Create the freelancer's QiCard payout account, or update mutable fields
        on an existing one. The phone field is immutable post-creation (account
        deletion + re-creation is the only path to change it — a future OTP
        flow could relax this). Holder name is freely editable because it is a
        payout-reconciliation label, not an auth credential.
        """
        provider = PaymentProvider(data.provider)
        existing = await self.db.execute(
            select(PaymentAccount).where(
                PaymentAccount.user_id == user.id,
                PaymentAccount.provider == provider,
            )
        )
        account = existing.scalar_one_or_none()

        if account is not None:
            # Upsert: update holder name when provided; ignore phone changes.
            if data.qi_card_holder_name is not None:
                account.qi_card_holder_name = data.qi_card_holder_name
            await self.db.flush()
            await self.db.refresh(account)
            logger.info("Payment account updated: user=%s provider=%s", user.id, provider.value)
            return account

        external_id = f"qc_acct_{uuid.uuid4().hex[:12]}"
        account = PaymentAccount(
            user_id=user.id,
            provider=provider,
            status=PaymentAccountStatus.VERIFIED,
            external_account_id=external_id,
            qi_card_phone=data.qi_card_phone,
            qi_card_holder_name=data.qi_card_holder_name,
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
            raise NotFoundError("Milestone")

        result = await self.db.execute(
            select(Contract).where(Contract.id == milestone.contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            raise NotFoundError("Contract")

        if contract.client_id != client.id:
            raise ForbiddenError("Only the client can fund escrow")

        if milestone.status not in (MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS):
            raise BadRequestError(f"Cannot fund escrow for milestone with status '{milestone.status.value}'")

        existing = await self.db.execute(
            select(Escrow).where(
                Escrow.milestone_id == milestone.id,
                Escrow.status.in_([EscrowStatus.FUNDED, EscrowStatus.PENDING]),
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestError("Escrow already funded or pending for this milestone")

        fees = self._calculate_fees(milestone.amount)
        order_id = f"escrow-{milestone.id}"

        # Server-controlled redirect URLs — never user-supplied (SSRF protection).
        # sig = HMAC(SECRET_KEY, order_id): ties the success URL to our server so
        # a user cannot bypass Qi Card by hitting the success URL directly with their
        # known order_id. Qi Card preserves existing query params when appending CartID.
        sig = self._sign_order_id(order_id)
        base = f"https://{settings.DOMAIN}"
        success_url = f"{base}/api/v1/payments/qi-card/success?sig={sig}"
        failure_url = f"{base}/api/v1/payments/qi-card/failure?sig={sig}"
        cancel_url  = f"{base}/api/v1/payments/qi-card/cancel?sig={sig}"

        # Initiate Qi Card payment (milestone.amount is already IQD).
        # Round to the nearest whole IQD (Qi Card requires int amounts); plain
        # int() truncates toward zero and systematically underpays by up to 0.99.
        amount_iqd_int = int(
            Decimal(str(fees["amount"])).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
        try:
            qi_result = await self.qi_card.create_payment(
                amount_iqd=amount_iqd_int,
                order_id=order_id,
                success_url=success_url,
                failure_url=failure_url,
                cancel_url=cancel_url,
            )
        except QiCardError as e:
            logger.exception("Qi Card error in fund_escrow: %s", e)
            # Explicit rollback mirrors place_order's pattern — drops any
            # validation-time selects or partial state from the session so
            # the outer request gets a clean slate on the error path.
            await self.db.rollback()
            raise ExternalServiceError("Payment gateway error. Please try again later.") from e

        qi_payment_id = order_id   # Qi Card uses our orderId to identify the payment
        amount_iqd = qi_result["amount_iqd"]
        form_url = qi_result.get("link")

        # Create transaction + escrow and flush them together. BaseModel.id is
        # generated client-side (uuid.uuid4 default), so transaction.id is
        # available before any DB round-trip and can be used as the escrow's
        # funding_transaction_id FK without an intermediate flush. This removes
        # the window where the Transaction was persisted but the Escrow wasn't.
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
        self.db.add_all([transaction, escrow])
        try:
            await self.db.flush()
        except IntegrityError as e:
            await self.db.rollback()
            raise ConflictError("Duplicate or constraint violation") from e
        except SQLAlchemyError:
            await self.db.rollback()
            raise

        logger.info(
            "Qi Card payment initiated: milestone=%s payment_id=%s amount_iqd=%s",
            data.milestone_id, qi_payment_id, amount_iqd,
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

    async def confirm_qi_card_payment(self, order_id: str, sig: str = "") -> bool:
        """
        Called when Qi Card redirects the browser to successUrl?CartID=<order_id>.
        Marks the escrow as FUNDED and transaction as COMPLETED.
        order_id is our "escrow-<milestone_id>" or "gig-order-<order_id>" string.

        sig must match HMAC(SECRET_KEY, order_id).  Empty sig is rejected so that
        a user cannot fake payment by hitting this URL directly with their order_id.
        """
        if not self._verify_order_sig(order_id, sig):
            logger.warning(
                "Qi Card success: invalid or missing signature for order_id=%s — possible forgery attempt",
                order_id,
            )
            return False

        # with_for_update ensures duplicate Qi Card success redirects (which do
        # happen in practice) are serialised — only the first one processes.
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.external_transaction_id == order_id,
                Transaction.provider == PaymentProvider.QI_CARD,
                Transaction.transaction_type == TransactionType.ESCROW_FUND,
            ).with_for_update()
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            logger.warning("Qi Card success: no transaction found for order_id=%s", order_id)
            return False

        if transaction.status == TransactionStatus.COMPLETED:
            logger.info("Qi Card webhook: already processed order_id=%s", order_id)
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
            _record_escrow_transition("pending", "funded")

            # Notify freelancer that funds are safely in escrow (contract-milestone
            # path only — service orders are handled by the in-progress transition
            # below and have their own ORDER_* notification flow).
            if escrow.milestone_id is not None:
                amount_int = int(escrow.freelancer_amount)
                await notify(
                    self.db,
                    user_id=escrow.freelancer_id,
                    type=NotificationType.MILESTONE_FUNDED,
                    title_ar="تم إيداع المبلغ في الضمان",
                    title_en="Milestone funded",
                    message_ar=(
                        f"تم إيداع {amount_int:,} د.ع "
                        "في الضمان للمرحلة — يمكنك بدء العمل"
                    ),
                    message_en=(
                        f"{amount_int:,} IQD is held in escrow — "
                        "you can start working on this milestone"
                    ),
                    link_type="contract",
                    link_id=escrow.contract_id,
                    actor_id=escrow.client_id,
                )

        # For service orders: transition the ServiceOrder from PENDING → IN_PROGRESS so
        # the freelancer can start work. Without this, mark_delivered() always rejects
        # because it requires IN_PROGRESS, breaking the entire service order lifecycle.
        #
        # The "gig-order-" prefix on the external order_id is preserved for backward
        # compatibility with in-flight Qi Card records created before the rename —
        # changing it would orphan payments that are mid-flow.
        if order_id.startswith("gig-order-"):
            try:
                service_order_id = uuid.UUID(order_id[len("gig-order-"):])
                so_result = await self.db.execute(
                    select(ServiceOrder).where(ServiceOrder.id == service_order_id).with_for_update()
                )
                service_order = so_result.scalar_one_or_none()
                if service_order and service_order.status == ServiceOrderStatus.PENDING:
                    # F3: if the service has requirement questions, wait for client answers first
                    from app.models.service import Service as _Service  # noqa: PLC0415
                    svc_result = await self.db.execute(
                        select(_Service).where(_Service.id == service_order.service_id)
                    )
                    linked_service = svc_result.scalar_one_or_none()
                    if linked_service and linked_service.requirement_questions:
                        service_order.status = ServiceOrderStatus.PENDING_REQUIREMENTS
                        logger.info(
                            "ServiceOrder %s → PENDING_REQUIREMENTS (has questions)",
                            service_order_id,
                        )
                    else:
                        service_order.status = ServiceOrderStatus.IN_PROGRESS
                        logger.info(
                            "ServiceOrder %s → IN_PROGRESS after payment confirmed",
                            service_order_id,
                        )
            except (ValueError, AttributeError) as exc:
                logger.warning(
                    "Could not parse service_order_id from order_id=%s: %s", order_id, exc
                )

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

    async def handle_qi_card_payment_failed(self, order_id: str, sig: str = "") -> bool:
        """Mark transaction as FAILED when Qi Card redirects to failureUrl or cancelUrl."""
        if not self._verify_order_sig(order_id, sig):
            logger.warning("Qi Card failure/cancel: invalid signature for order_id=%s", order_id)
            return False

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
            _record_escrow_transition("pending", "refunded")

        await self.db.flush()
        logger.info("Qi Card payment failed/cancelled: order_id=%s", order_id)
        return True

    # === Escrow: Release (called when milestone approved or gig order completed) ===

    async def _release_locked_escrow(self, escrow: Escrow) -> EscrowReleaseResponse:
        """
        Internal: create ledger transactions and mark an already-locked escrow as
        RELEASED. Caller must have acquired with_for_update() on the escrow row
        before calling this method.
        """
        # Platform fee transaction — platform earns the fee (net_amount = platform_fee).
        # Note: net_amount must be > 0 per DB constraint; platform_fee is always > 0
        # because of the ck_escrow_fee_non_negative + ck_escrow_freelancer_le_total
        # constraints which guarantee platform_fee = amount - freelancer_amount > 0.
        fee_tx = Transaction(
            transaction_type=TransactionType.PLATFORM_FEE,
            status=TransactionStatus.COMPLETED,
            amount=escrow.platform_fee,
            currency=escrow.currency,
            platform_fee=escrow.platform_fee,
            net_amount=escrow.platform_fee,  # was 0 — violated net_amount > 0 constraint
            payer_id=escrow.freelancer_id,
            contract_id=escrow.contract_id,
            milestone_id=escrow.milestone_id,
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
            milestone_id=escrow.milestone_id,
            provider=PaymentProvider.QI_CARD,
            external_transaction_id=f"release_{uuid.uuid4().hex[:12]}",
            description="Payment released to freelancer balance",
            completed_at=datetime.now(UTC),
        )
        self.db.add(release_tx)
        await self.db.flush()

        # Optimistic-lock UPDATE: WHERE id=... AND version=:expected. If a
        # racing coroutine already released this escrow (would only be possible
        # if the FOR UPDATE row lock was bypassed), the rowcount comes back 0
        # and we refuse to record a duplicate release.
        expected_version = escrow.version
        now = datetime.now(UTC)
        update_result = await self.db.execute(
            update(Escrow)
            .where(
                Escrow.id == escrow.id,
                Escrow.version == expected_version,
                Escrow.status == EscrowStatus.FUNDED,
            )
            .values(
                status=EscrowStatus.RELEASED,
                released_at=now,
                release_transaction_id=release_tx.id,
                version=expected_version + 1,
            )
            .execution_options(synchronize_session=False)
        )
        if update_result.rowcount != 1:
            # Someone else flipped the row between our FOR UPDATE read and now.
            # Raising aborts the outer transaction so the ledger transactions
            # we just flushed get rolled back — no phantom release.
            raise ConflictError(
                "Escrow state changed concurrently (version mismatch); release aborted"
            )
        _record_escrow_transition("funded", "released")

        # Keep the in-memory ORM object consistent with what we just wrote.
        escrow.status = EscrowStatus.RELEASED
        escrow.released_at = now
        escrow.release_transaction_id = release_tx.id
        escrow.version = expected_version + 1

        logger.info(
            "Escrow released: escrow=%s milestone=%s amount=%s version=%d",
            escrow.id, escrow.milestone_id, escrow.freelancer_amount, escrow.version,
        )

        amount_iqd = int(escrow.freelancer_amount)
        await notify(
            self.db,
            user_id=escrow.freelancer_id,
            type=NotificationType.PAYMENT_RECEIVED,
            title_ar="تم استلام دفعة",
            title_en="Payment received",
            message_ar=f"تم تحرير مبلغ {amount_iqd:,} د.ع إلى رصيدك",
            message_en=f"{amount_iqd:,} IQD has been released to your balance",
            link_type="contract",
            link_id=escrow.contract_id,
            actor_id=escrow.client_id,
        )

        return EscrowReleaseResponse(
            escrow_id=escrow.id,
            milestone_id=escrow.milestone_id,
            amount=escrow.amount,
            freelancer_amount=escrow.freelancer_amount,
            status="released",
            message=f"${escrow.freelancer_amount:.2f} added to freelancer balance",
        )

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
        return await self._release_locked_escrow(escrow)

    async def release_escrow_by_id(
        self, escrow_id: uuid.UUID
    ) -> EscrowReleaseResponse | None:
        """
        Release escrow by its primary key. Used by admin manual payout and gig
        order completion — works for both contract-milestone and gig-order escrows.

        Blocks release when the freelancer's QiCard account is missing the phone
        or cardholder name, since the admin cannot reconcile a manual payout
        without both fields. Gig-order auto-completion bypasses this check by
        calling ``_release_locked_escrow`` directly.
        """
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.id == escrow_id,
                Escrow.status == EscrowStatus.FUNDED,
            ).with_for_update()
        )
        escrow = result.scalar_one_or_none()
        if not escrow:
            return None

        acct_result = await self.db.execute(
            select(PaymentAccount.qi_card_phone, PaymentAccount.qi_card_holder_name).where(
                PaymentAccount.user_id == escrow.freelancer_id,
                PaymentAccount.provider == PaymentProvider.QI_CARD,
                PaymentAccount.status == PaymentAccountStatus.VERIFIED,
            )
        )
        acct_row = acct_result.first()
        if not acct_row or not acct_row[0] or not acct_row[1]:
            raise BadRequestError(
                "Freelancer's QiCard payout details are incomplete (phone + cardholder "
                "name required). Ask them to finish payment-account setup before release."
            )

        return await self._release_locked_escrow(escrow)

    # === Escrow: Refund ===

    async def refund_escrow_by_service_order(
        self, service_order_id: uuid.UUID, reason: str = "Dispute resolved: refund to client"
    ) -> bool:
        """Refund a service-order escrow (used by dispute resolution)."""
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.service_order_id == service_order_id,
                Escrow.status.in_([EscrowStatus.FUNDED, EscrowStatus.DISPUTED]),
            ).with_for_update()
        )
        escrow = result.scalar_one_or_none()
        if not escrow:
            return False

        refund_tx = Transaction(
            transaction_type=TransactionType.ESCROW_REFUND,
            status=TransactionStatus.PROCESSING,  # Manual Qi Card portal refund required
            amount=escrow.amount,
            currency=escrow.currency,
            platform_fee=0,
            net_amount=escrow.amount,
            payee_id=escrow.client_id,
            provider=PaymentProvider.QI_CARD,
            external_transaction_id=f"refund_{uuid.uuid4().hex[:12]}",
            description=reason,
        )
        self.db.add(refund_tx)
        prev_status = "disputed" if escrow.status == EscrowStatus.DISPUTED else "funded"
        escrow.status = EscrowStatus.REFUNDED
        escrow.released_at = datetime.now(UTC)
        _record_escrow_transition(prev_status, "refunded")
        await self.db.flush()

        refund_amount = int(escrow.amount)
        await notify(
            self.db,
            user_id=escrow.client_id,
            type=NotificationType.PAYMENT_RECEIVED,
            title_ar="تم بدء استرداد المبلغ",
            title_en="Refund initiated",
            message_ar=f"سيتم إعادة {refund_amount:,} د.ع إلى حسابك خلال 3-5 أيام عمل.",
            message_en=f"{refund_amount:,} IQD will be returned to you within 3-5 business days.",
            link_type="service_order",
            link_id=escrow.service_order_id,
        )
        logger.info(
            "Service order escrow refunded: service_order_id=%s amount=%s",
            service_order_id, escrow.amount,
        )
        return True

    async def refund_escrow(
        self, milestone_id: uuid.UUID, reason: str = "Milestone cancelled"
    ) -> bool:
        """Refund escrow to client via Qi Card."""
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.milestone_id == milestone_id,
                Escrow.status == EscrowStatus.FUNDED,
            ).with_for_update()
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
        amount_iqd = int(
            Decimal(str(escrow.amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

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

        prev_status = "disputed" if escrow.status == EscrowStatus.DISPUTED else "funded"
        escrow.status = EscrowStatus.REFUNDED
        escrow.released_at = datetime.now(UTC)
        _record_escrow_transition(prev_status, "refunded")

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
            raise NotFoundError("Payment account")

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
            raise BadRequestError(f"Insufficient balance. Available: {available:,.0f} IQD")

        # Enforce minimum payout to prevent tiny withdrawals whose manual
        # admin-processing cost exceeds their value.
        if data.amount < settings.MINIMUM_PAYOUT_IQD:
            raise BadRequestError(
                f"Minimum payout is {settings.MINIMUM_PAYOUT_IQD:,.0f} IQD"
            )

        amount_iqd = int(
            Decimal(str(data.amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )

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
                f"Qi Card payout: {amount_iqd:,} IQD "
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
        except SQLAlchemyError:
            raise

        logger.info(
            "Payout requested: freelancer=%s amount=%s (%s IQD) provider=%s",
            freelancer.id, data.amount, f"{amount_iqd:,}", account.provider.value,
        )

        # Notify freelancer of payout status
        payout_status = payout_tx.status.value
        if payout_status == "completed":
            await notify(
                self.db,
                user_id=freelancer.id,
                type=NotificationType.PAYOUT_COMPLETED,
                title_ar="تم سحب الأموال بنجاح",
                title_en="Payout completed",
                message_ar=f"تم تحويل {amount_iqd:,} د.ع إلى حسابك",
                message_en=f"{amount_iqd:,} IQD has been transferred to your account",
                link_type=None,
                link_id=None,
            )

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

    async def mark_payout_paid(
        self,
        transaction_id: uuid.UUID,
        admin: User,
        note: str | None = None,
        ip_address: str | None = None,
    ) -> Transaction:
        """
        Admin-triggered completion of a freelancer payout.

        Qi Card has no payout API (Known Issue #3): admins send the money
        manually through the Qi Card merchant dashboard, then call this
        endpoint to flip the Transaction from PROCESSING to COMPLETED so
        the freelancer sees the payout as received.

        - FOR UPDATE locks the transaction row to block double-marking.
        - Only admins / superusers should reach this via the endpoint layer.
        - Writes an audit log entry and notifies the freelancer.
        """
        from app.models.admin_audit import AdminAuditAction
        from app.services.audit_service import AuditService

        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .with_for_update()
        )
        tx = result.scalar_one_or_none()
        if tx is None:
            raise NotFoundError("Payout transaction")

        if tx.transaction_type != TransactionType.PAYOUT:
            raise BadRequestError("Transaction is not a payout")
        if tx.status != TransactionStatus.PROCESSING:
            raise BadRequestError(
                f"Only PROCESSING payouts can be marked paid (current: {tx.status.value})"
            )

        tx.status = TransactionStatus.COMPLETED
        tx.completed_at = datetime.now(UTC)
        if note:
            # Preserve the original description and append the admin note for context.
            tx.description = f"{tx.description or ''} | marked paid: {note[:200]}".strip(" |")

        try:
            await self.db.flush()
        except SQLAlchemyError:
            raise

        # Best-effort audit log. AuditService.log swallows its own failures so
        # the money-state transition is never blocked by a logging hiccup.
        await AuditService(self.db).log(
            admin_id=admin.id,
            action=AdminAuditAction.PAYOUT_MARKED_PAID,
            target_type="transaction",
            target_id=tx.id,
            amount=float(tx.amount),
            currency=tx.currency,
            ip_address=ip_address,
            details={"note": note} if note else None,
        )

        if tx.payee_id is not None:
            amount_iqd = int(
                Decimal(str(tx.amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            )
            await notify(
                self.db,
                user_id=tx.payee_id,
                type=NotificationType.PAYOUT_COMPLETED,
                title_ar="تم سحب الأموال بنجاح",
                title_en="Payout completed",
                message_ar=f"تم تحويل {amount_iqd:,} د.ع إلى حسابك",
                message_en=f"{amount_iqd:,} IQD has been transferred to your account",
                link_type=None,
                link_id=None,
            )

        logger.info(
            "Payout marked paid: tx=%s admin=%s amount=%s %s",
            tx.id, admin.id, tx.amount, tx.currency,
        )
        return tx

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

        # Payouts already paid by admin (status=COMPLETED). Subtracting these
        # from earnings gives the "money that has settled to Qi Card" view.
        paid_out_completed_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.payee_id == user.id,
                Transaction.transaction_type == TransactionType.PAYOUT,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )
        total_paid_out_completed = paid_out_completed_result.scalar() or 0.0

        # Payouts the freelancer requested but the admin hasn't marked paid yet.
        pending_payout_result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.payee_id == user.id,
                Transaction.transaction_type == TransactionType.PAYOUT,
                Transaction.status == TransactionStatus.PROCESSING,
            )
        )
        pending_payout = pending_payout_result.scalar() or 0.0

        # The available balance check and the request_payout validator both
        # subtract pending+completed — a freelancer can't request a second
        # payout that would overdraw their released balance.
        total_paid_out = total_paid_out_completed + pending_payout

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
            "available_balance": max(0.0, round(total_earned - total_paid_out, 2)),
            "total_paid_out": total_paid_out_completed,
            "pending_payout": pending_payout,
            "total_platform_fees": total_fees,
            "transaction_count": tx_count,
            "payment_accounts": accounts,
        }
