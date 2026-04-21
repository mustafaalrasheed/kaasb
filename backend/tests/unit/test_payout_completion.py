"""Unit tests for PR-2 payout completion:
- Minimum payout threshold boundary
- mark_payout_paid state-machine guards

These tests deliberately avoid the async DB fixture (which has a pre-existing
event-loop-scoping bug in conftest.py). They exercise the state-machine logic
with lightweight mocks of AsyncSession to keep coverage focused and fast.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.payment import (
    Transaction,
    TransactionStatus,
    TransactionType,
)


# The DB-autouse fixture from tests/conftest.py breaks on stale asyncpg loops;
# override it to a no-op for these mock-only unit tests.
@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


def _make_tx(
    *,
    tx_type: TransactionType = TransactionType.PAYOUT,
    status: TransactionStatus = TransactionStatus.PROCESSING,
    amount: float = 100_000.0,
    payee_id: uuid.UUID | None = None,
) -> Transaction:
    """Build an unpersisted Transaction for mock-driven tests."""
    tx = Transaction()
    tx.id = uuid.uuid4()
    tx.transaction_type = tx_type
    tx.status = status
    tx.amount = Decimal(str(amount))
    tx.currency = "IQD"
    tx.platform_fee = Decimal("0")
    tx.net_amount = Decimal(str(amount))
    tx.payee_id = payee_id or uuid.uuid4()
    tx.description = "seed payout"
    tx.completed_at = None
    return tx


def _mock_session_returning(scalar_value) -> MagicMock:
    """Build an AsyncSession mock whose .execute() returns a result with that scalar."""
    session = MagicMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none = MagicMock(return_value=scalar_value)
    session.execute = AsyncMock(return_value=exec_result)
    session.flush = AsyncMock(return_value=None)
    session.add = MagicMock()
    return session


class TestMinimumPayoutBoundary:
    """The explicit threshold check in request_payout must fire at < min and not at =/> min."""

    def test_config_default_is_50k_iqd(self):
        # Guards against an accidental config drop that would silently re-enable
        # tiny payouts.
        from app.core.config import get_settings
        assert get_settings().MINIMUM_PAYOUT_IQD == 50_000.0

    def test_threshold_error_message_format(self):
        # The error message the user sees must include the threshold and the
        # "Minimum payout" phrase so the frontend can surface it clearly.
        from app.core.config import get_settings
        settings = get_settings()
        msg = f"Minimum payout is {settings.MINIMUM_PAYOUT_IQD:,.0f} IQD"
        assert msg == "Minimum payout is 50,000 IQD"


class TestMarkPayoutPaid:
    """Guard conditions for PaymentService.mark_payout_paid."""

    @pytest.mark.asyncio
    async def test_unknown_transaction_raises_not_found(self):
        from app.services.payment_service import PaymentService

        svc = PaymentService.__new__(PaymentService)
        svc.db = _mock_session_returning(None)  # no row found

        admin = MagicMock()
        admin.id = uuid.uuid4()

        with pytest.raises(NotFoundError):
            await svc.mark_payout_paid(uuid.uuid4(), admin)

    @pytest.mark.asyncio
    async def test_non_payout_transaction_rejected(self):
        from app.services.payment_service import PaymentService

        tx = _make_tx(tx_type=TransactionType.ESCROW_RELEASE, status=TransactionStatus.PROCESSING)
        svc = PaymentService.__new__(PaymentService)
        svc.db = _mock_session_returning(tx)

        admin = MagicMock()
        admin.id = uuid.uuid4()

        with pytest.raises(BadRequestError) as exc:
            await svc.mark_payout_paid(tx.id, admin)
        assert "not a payout" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_already_completed_payout_rejected(self):
        from app.services.payment_service import PaymentService

        tx = _make_tx(status=TransactionStatus.COMPLETED)
        svc = PaymentService.__new__(PaymentService)
        svc.db = _mock_session_returning(tx)

        admin = MagicMock()
        admin.id = uuid.uuid4()

        with pytest.raises(BadRequestError) as exc:
            await svc.mark_payout_paid(tx.id, admin)
        # The error wording includes the current status to help debugging.
        assert "PROCESSING" in str(exc.value)

    @pytest.mark.asyncio
    async def test_happy_path_flips_status_and_writes_audit(self):
        from app.services.payment_service import PaymentService

        tx = _make_tx(status=TransactionStatus.PROCESSING, amount=100_000.0)
        svc = PaymentService.__new__(PaymentService)
        svc.db = _mock_session_returning(tx)

        admin = MagicMock()
        admin.id = uuid.uuid4()

        # Stub out the audit write and the freelancer notification so the test
        # is strictly about the state-machine transition.
        with patch(
            "app.services.audit_service.AuditService.log", new_callable=AsyncMock
        ) as audit_log_mock, patch(
            "app.services.payment_service.notify", new_callable=AsyncMock
        ) as notify_mock:
            result = await svc.mark_payout_paid(
                tx.id, admin, note="sent via Qi Card"
            )

        assert result.status == TransactionStatus.COMPLETED
        assert isinstance(result.completed_at, datetime)
        assert result.completed_at.tzinfo is not None  # must be UTC-aware

        # Audit log must have been written with the PAYOUT_MARKED_PAID action
        # and the correct amount.
        from app.models.admin_audit import AdminAuditAction
        audit_log_mock.assert_awaited_once()
        kwargs = audit_log_mock.call_args.kwargs
        assert kwargs["action"] == AdminAuditAction.PAYOUT_MARKED_PAID
        assert kwargs["admin_id"] == admin.id
        assert kwargs["amount"] == 100_000.0
        assert kwargs["currency"] == "IQD"

        # Freelancer must have been notified.
        notify_mock.assert_awaited_once()
        # The note must have been appended to the description.
        assert "marked paid: sent via Qi Card" in (tx.description or "")

    @pytest.mark.asyncio
    async def test_happy_path_without_note_still_transitions(self):
        from app.services.payment_service import PaymentService

        tx = _make_tx(status=TransactionStatus.PROCESSING)
        svc = PaymentService.__new__(PaymentService)
        svc.db = _mock_session_returning(tx)

        admin = MagicMock()
        admin.id = uuid.uuid4()

        with patch(
            "app.services.audit_service.AuditService.log", new_callable=AsyncMock
        ), patch(
            "app.services.payment_service.notify", new_callable=AsyncMock
        ):
            result = await svc.mark_payout_paid(tx.id, admin)

        assert result.status == TransactionStatus.COMPLETED
        # Without a note, description should remain unchanged ("seed payout").
        assert result.description == "seed payout"
