"""Unit tests for PR-3 observability:
- Escrow state-transition counter emits from payment_service helper
- Audit-failure counter emits when AuditService.log raises
- /health/scheduler returns 503 when the tracked job is stale
- flag_stuck_pending_transactions logs + updates the gauge

All tests override the DB autouse fixture to stay in pure-unit territory
(no event-loop scoping flake).
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# Package-level autouse fixture in tests/conftest.py does DB setup that
# depends on a running Postgres and a loop-scoped engine; skip for these
# pure-unit tests.
@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


class TestEscrowTransitionCounter:
    """_record_escrow_transition must bump the Prometheus counter with the right labels."""

    def test_emits_with_correct_labels(self):
        from app.services.payment_service import _record_escrow_transition

        with patch(
            "app.middleware.monitoring.ESCROW_STATE_TRANSITIONS"
        ) as counter_mock:
            _record_escrow_transition("funded", "released")

        counter_mock.labels.assert_called_once_with(
            from_status="funded", to_status="released"
        )
        counter_mock.labels.return_value.inc.assert_called_once_with()

    def test_swallows_metric_errors(self):
        """A failure to emit metrics must never propagate to callers."""
        from app.services.payment_service import _record_escrow_transition

        # Patch the import to raise — exactly the failure mode we guard against.
        with patch(
            "app.middleware.monitoring.ESCROW_STATE_TRANSITIONS",
            side_effect=RuntimeError("prometheus down"),
        ):
            # Must not raise.
            _record_escrow_transition("funded", "released")


class TestAuditFailureCounter:
    """AuditService.log bumps AUDIT_LOG_FAILURES on exception — primary ops signal."""

    @pytest.mark.asyncio
    async def test_counter_fires_when_flush_raises(self):
        from app.models.admin_audit import AdminAuditAction
        from app.services.audit_service import AuditService

        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock(side_effect=RuntimeError("db down"))
        svc = AuditService(session)

        with patch(
            "app.middleware.monitoring.AUDIT_LOG_FAILURES"
        ) as counter_mock:
            result = await svc.log(
                admin_id=None,
                action=AdminAuditAction.ESCROW_RELEASED,
                target_type="escrow",
            )

        # AuditService.log never raises — returns None on failure.
        assert result is None
        counter_mock.labels.assert_called_once_with(action="escrow_released")
        counter_mock.labels.return_value.inc.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_counter_does_not_fire_on_success(self):
        from app.models.admin_audit import AdminAuditAction
        from app.services.audit_service import AuditService

        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock(return_value=None)
        svc = AuditService(session)

        with patch(
            "app.middleware.monitoring.AUDIT_LOG_FAILURES"
        ) as counter_mock:
            result = await svc.log(
                admin_id=None,
                action=AdminAuditAction.ESCROW_RELEASED,
                target_type="escrow",
            )

        assert result is not None
        counter_mock.labels.assert_not_called()


class TestSchedulerHealthProbe:
    """/health/scheduler must flag stale jobs."""

    @pytest.mark.asyncio
    async def test_all_recent_returns_200(self):
        from app.api.v1.endpoints.health import scheduler_health

        now = datetime.now(UTC)
        with patch(
            "app.tasks.scheduler.get_last_run_timestamps",
            new_callable=AsyncMock,
            return_value={"marketplace_daily": now - timedelta(hours=1)},
        ):
            response = await scheduler_health()

        assert response.status_code == 200
        body = json.loads(response.body)
        assert body["ok"] is True
        assert body["jobs"]["marketplace_daily"]["stale"] is False

    @pytest.mark.asyncio
    async def test_stale_job_returns_503(self):
        from app.api.v1.endpoints.health import scheduler_health

        now = datetime.now(UTC)
        with patch(
            "app.tasks.scheduler.get_last_run_timestamps",
            new_callable=AsyncMock,
            return_value={"marketplace_daily": now - timedelta(hours=48)},
        ):
            response = await scheduler_health()

        assert response.status_code == 503
        body = json.loads(response.body)
        assert body["ok"] is False
        assert body["jobs"]["marketplace_daily"]["stale"] is True

    @pytest.mark.asyncio
    async def test_never_run_returns_503(self):
        from app.api.v1.endpoints.health import scheduler_health

        with patch(
            "app.tasks.scheduler.get_last_run_timestamps",
            new_callable=AsyncMock,
            return_value={"marketplace_daily": None},
        ):
            response = await scheduler_health()

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_redis_unreachable_returns_503(self):
        from app.api.v1.endpoints.health import scheduler_health

        with patch(
            "app.tasks.scheduler.get_last_run_timestamps",
            new_callable=AsyncMock,
            side_effect=RuntimeError("redis down"),
        ):
            response = await scheduler_health()

        assert response.status_code == 503
        assert b"scheduler state unavailable" in response.body


class TestFlagStuckPending:
    """marketplace_tasks.flag_stuck_pending_transactions logs + updates the gauge."""

    @pytest.mark.asyncio
    async def test_zero_stuck_still_sets_gauge_to_zero(self):
        from app.tasks.marketplace_tasks import flag_stuck_pending_transactions

        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=0)))

        with patch(
            "app.middleware.monitoring.STUCK_PENDING_TRANSACTIONS"
        ) as gauge_mock:
            count = await flag_stuck_pending_transactions(session)

        assert count == 0
        gauge_mock.set.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_nonzero_stuck_updates_gauge_and_logs(self, caplog):
        from app.tasks.marketplace_tasks import flag_stuck_pending_transactions

        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=7)))

        with patch(
            "app.middleware.monitoring.STUCK_PENDING_TRANSACTIONS"
        ) as gauge_mock, caplog.at_level("WARNING"):
            count = await flag_stuck_pending_transactions(session, min_age_minutes=30)

        assert count == 7
        gauge_mock.set.assert_called_once_with(7)
        assert any("7 PENDING transactions" in r.message for r in caplog.records)
