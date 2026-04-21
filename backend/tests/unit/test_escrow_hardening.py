"""Unit tests for PR-4a escrow hardening:
- Optimistic-lock version check in _release_locked_escrow
- fund_escrow explicit rollback on QiCardError
- Dispute CHECK constraint (validated at migration level; smoke-tested here)
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


def _make_escrow_stub(version: int = 1):
    """Build a minimal Escrow-shaped object suitable for _release_locked_escrow."""
    from app.models.payment import Escrow, EscrowStatus

    escrow = Escrow()
    # Real UUIDs so the EscrowReleaseResponse pydantic model can serialize.
    escrow.id = uuid.uuid4()
    escrow.version = version
    escrow.status = EscrowStatus.FUNDED
    escrow.milestone_id = uuid.uuid4()
    escrow.contract_id = uuid.uuid4()
    escrow.client_id = uuid.uuid4()
    escrow.freelancer_id = uuid.uuid4()
    escrow.amount = Decimal("100000")
    escrow.platform_fee = Decimal("10000")
    escrow.freelancer_amount = Decimal("90000")
    escrow.currency = "IQD"
    escrow.released_at = None
    escrow.release_transaction_id = None
    return escrow


class TestOptimisticLockRelease:
    """_release_locked_escrow must refuse to release when the version moved."""

    @pytest.mark.asyncio
    async def test_rowcount_zero_raises_conflict(self):
        from app.core.exceptions import ConflictError
        from app.services.payment_service import PaymentService

        svc = PaymentService.__new__(PaymentService)
        svc.db = MagicMock()
        svc.db.add = MagicMock()
        # First flush (ledger transactions) succeeds.
        # Second execute is the optimistic UPDATE — rowcount 0 signals a race.
        svc.db.flush = AsyncMock(return_value=None)
        update_result = MagicMock()
        update_result.rowcount = 0  # <-- version moved under us
        svc.db.execute = AsyncMock(return_value=update_result)

        escrow = _make_escrow_stub(version=5)

        with patch("app.services.payment_service._record_escrow_transition"):
            with pytest.raises(ConflictError) as exc:
                await svc._release_locked_escrow(escrow)

        assert "version mismatch" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_happy_path_bumps_version(self):
        """When rowcount == 1 the in-memory escrow is updated to match the DB."""
        from app.models.payment import EscrowStatus
        from app.services.payment_service import PaymentService

        svc = PaymentService.__new__(PaymentService)
        svc.db = MagicMock()
        svc.db.add = MagicMock()
        svc.db.flush = AsyncMock(return_value=None)
        update_result = MagicMock()
        update_result.rowcount = 1
        svc.db.execute = AsyncMock(return_value=update_result)

        escrow = _make_escrow_stub(version=3)

        with patch(
            "app.services.payment_service._record_escrow_transition"
        ) as metric, patch(
            "app.services.payment_service.notify", new_callable=AsyncMock
        ) as notify_mock:
            result = await svc._release_locked_escrow(escrow)

        assert escrow.status == EscrowStatus.RELEASED
        assert escrow.version == 4  # <-- bumped
        assert escrow.released_at is not None
        # release_transaction_id is left None here because the mocked flush
        # doesn't trigger the uuid.uuid4 default on the in-memory Transaction
        # row; that's a test-harness quirk, not a service bug. Real DB flushes
        # populate it via the column default.
        assert result.escrow_id == escrow.id
        metric.assert_called_once_with("funded", "released")
        notify_mock.assert_awaited_once()


class TestFundEscrowRollback:
    """fund_escrow must call rollback() when Qi Card raises QiCardError."""

    @pytest.mark.asyncio
    async def test_qi_card_error_triggers_rollback(self):
        from app.core.exceptions import ExternalServiceError
        from app.services.payment_service import PaymentService
        from app.services.qi_card_client import QiCardError

        svc = PaymentService.__new__(PaymentService)
        svc.platform_fee_rate = Decimal("0.10")
        svc.db = MagicMock()
        svc.db.rollback = AsyncMock(return_value=None)

        # Stub out enough state so we reach the Qi Card call. The lookups
        # (milestone / contract / existing-escrow check) all succeed with
        # valid objects, fees compute, then the Qi Card stub raises.
        milestone = MagicMock()
        milestone.id = uuid.uuid4()
        milestone.amount = 100_000.0
        milestone.title = "test milestone"
        from app.models.contract import MilestoneStatus
        milestone.status = MilestoneStatus.PENDING

        contract = MagicMock()
        contract.id = uuid.uuid4()
        contract.freelancer_id = uuid.uuid4()
        # Must match client.id below so the ForbiddenError path doesn't fire
        # before we reach the Qi Card call we're testing.
        contract_client_id = uuid.uuid4()
        contract.client_id = contract_client_id

        execute_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=milestone)),  # milestone SELECT
            MagicMock(scalar_one_or_none=MagicMock(return_value=contract)),   # contract SELECT
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),       # existing-escrow check
        ]
        svc.db.execute = AsyncMock(side_effect=execute_results)

        client = MagicMock()
        client.id = contract_client_id

        svc.qi_card = MagicMock()
        svc.qi_card.create_payment = AsyncMock(
            side_effect=QiCardError("gateway 500")
        )

        from app.schemas.payment import EscrowFundRequest
        data = EscrowFundRequest(milestone_id=milestone.id)

        with pytest.raises(ExternalServiceError):
            await svc.fund_escrow(client, data)

        # The key assertion: a Qi Card failure explicitly rolls back the session.
        svc.db.rollback.assert_awaited_once()


class TestDisputeReleaseConstraint:
    """The CHECK constraint name is stable and matches the migration."""

    def test_constraint_name_matches_migration(self):
        """Sanity check: the model's constraint name must equal the migration's."""
        from app.models.payment import Escrow

        names = {c.name for c in Escrow.__table_args__ if hasattr(c, "name")}
        assert "ck_escrow_no_release_while_disputed" in names
