"""
Unit tests for the F6 escalation ladder inside ``MessageFilterService``.

Pattern matches ``test_escrow_hardening``: service instantiated via
``__new__`` with a MagicMock ``db`` so we test the state machine without
Postgres. The DB calls we care about (``add`` / ``flush`` / ``execute``)
are stubbed; the notification fan-out is patched out because it uses
``asyncio.create_task`` to fire notifications in the background and we
don't want tasks leaking into other tests.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.models.message import ConversationType
from app.models.user import UserRole, UserStatus
from app.models.violation_log import ViolationAction


@pytest_asyncio.fixture(autouse=True)
async def _skip_real_db():
    """Override conftest's autouse setup_database — these tests use mocks."""
    yield


def _make_sender(violations: int = 0, suspended_until: datetime | None = None):
    """Build a User-shaped stub with the F6 fields the filter reads/writes."""
    from app.models.user import User

    u = User()
    u.id = uuid.uuid4()
    u.username = "alice"
    u.email = "alice@test.com"
    u.primary_role = UserRole.CLIENT
    u.status = UserStatus.ACTIVE
    u.is_superuser = False
    u.is_support = False
    u.chat_violations = violations
    u.chat_suspended_until = suspended_until
    return u


def _make_service():
    """Build a MessageFilterService with mocked db calls — no Postgres."""
    from app.services.message_filter_service import MessageFilterService

    svc = MessageFilterService.__new__(MessageFilterService)
    svc.db = MagicMock()
    svc.db.add = MagicMock()
    svc.db.flush = AsyncMock(return_value=None)
    # _execute for the admin-broadcast query on SUSPENDED — return no admins
    # so we don't fan out notifications during tests.
    empty_result = MagicMock()
    empty_result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    svc.db.execute = AsyncMock(return_value=empty_result)
    return svc


class TestAlreadySuspended:
    """A user with chat_suspended_until in the future is short-circuited."""

    @pytest.mark.asyncio
    async def test_active_suspension_blocks_without_touching_counter(self):
        svc = _make_service()
        sender = _make_sender(
            violations=3,
            suspended_until=datetime.now(UTC) + timedelta(hours=5),
        )

        with patch("app.services.message_filter_service.notify_background", new=AsyncMock()):
            outcome = await svc.process_message(sender, "any message at all")

        assert outcome.blocked is True
        assert outcome.code == "suspended"
        # Counter unchanged — active suspension doesn't compound.
        assert sender.chat_violations == 3
        # Short-circuit: no violation_log written, no flush.
        svc.db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_expired_suspension_lets_message_through(self):
        # chat_suspended_until in the past → treated as cleared.
        svc = _make_service()
        sender = _make_sender(
            violations=3,
            suspended_until=datetime.now(UTC) - timedelta(hours=1),
        )

        with patch("app.services.message_filter_service.notify_background", new=AsyncMock()):
            outcome = await svc.process_message(sender, "hello there")

        # Clean message, no violations → not blocked, not a warning.
        assert outcome.blocked is False
        assert outcome.warning is False


class TestEscalationLadder:
    """First violation warns, second blocks, third suspends 24h."""

    @pytest.mark.asyncio
    async def test_first_violation_warns_and_masks(self):
        svc = _make_service()
        sender = _make_sender(violations=0)

        with patch("app.services.message_filter_service.notify_background", new=AsyncMock()):
            outcome = await svc.process_message(sender, "email me at foo@bar.com")

        assert outcome.blocked is False
        assert outcome.warning is True
        assert outcome.code == "email"
        assert outcome.total_violations == 1
        # Contact info masked in the delivered content.
        assert "foo@bar.com" not in outcome.content
        # Counter bumped on the sender.
        assert sender.chat_violations == 1
        # ViolationLog inserted with WARNING action.
        svc.db.add.assert_called_once()
        log = svc.db.add.call_args[0][0]
        assert log.action_taken == ViolationAction.WARNING

    @pytest.mark.asyncio
    async def test_second_violation_blocks(self):
        svc = _make_service()
        sender = _make_sender(violations=1)  # already had 1 warning

        with patch("app.services.message_filter_service.notify_background", new=AsyncMock()):
            outcome = await svc.process_message(sender, "call 07701234567 please")

        assert outcome.blocked is True
        assert outcome.warning is False
        assert outcome.code == "phone"
        assert outcome.total_violations == 2
        assert sender.chat_violations == 2
        # Still ACTIVE — BLOCKED doesn't set a suspension timestamp.
        assert sender.chat_suspended_until is None
        log = svc.db.add.call_args[0][0]
        assert log.action_taken == ViolationAction.BLOCKED

    @pytest.mark.asyncio
    async def test_third_violation_suspends_24h(self):
        svc = _make_service()
        sender = _make_sender(violations=2)  # one warning, one block

        before = datetime.now(UTC)
        with patch("app.services.message_filter_service.notify_background", new=AsyncMock()):
            outcome = await svc.process_message(sender, "move to whatsapp")
        after = datetime.now(UTC)

        assert outcome.blocked is True
        assert outcome.code == "suspended"
        assert outcome.total_violations == 3
        # Suspension window is ~24h from "now".
        assert sender.chat_suspended_until is not None
        delta = sender.chat_suspended_until - before
        assert timedelta(hours=23, minutes=59) <= delta <= (after - before) + timedelta(hours=24)
        log = svc.db.add.call_args[0][0]
        assert log.action_taken == ViolationAction.SUSPENDED

    @pytest.mark.asyncio
    async def test_fourth_violation_also_suspends(self):
        # Counter keeps climbing after the threshold — any offense past 3
        # re-suspends. This matters for unsuspend_chat (keeps violations
        # intact so repeat offenders stay on the "3+" suspend branch).
        svc = _make_service()
        sender = _make_sender(violations=5)

        with patch("app.services.message_filter_service.notify_background", new=AsyncMock()):
            outcome = await svc.process_message(sender, "signal me at foo@bar.com")

        assert outcome.blocked is True
        assert outcome.code == "suspended"
        assert outcome.total_violations == 6


class TestOrderConversationBypass:
    """ORDER threads let delivery URLs through but still catch email/phone."""

    @pytest.mark.asyncio
    async def test_url_allowed_in_order_thread(self):
        svc = _make_service()
        sender = _make_sender(violations=0)

        with patch("app.services.message_filter_service.notify_background", new=AsyncMock()):
            outcome = await svc.process_message(
                sender,
                "here's your delivery: https://drive.google.com/xyz",
                conversation_type=ConversationType.ORDER,
            )

        # URL allowed → no violation, clean content pass-through.
        assert outcome.blocked is False
        assert outcome.warning is False
        assert "drive.google.com" in outcome.content
        assert sender.chat_violations == 0
        svc.db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_still_blocked_in_order_thread(self):
        svc = _make_service()
        sender = _make_sender(violations=0)

        with patch("app.services.message_filter_service.notify_background", new=AsyncMock()):
            outcome = await svc.process_message(
                sender,
                "reply to foo@bar.com when ready",
                conversation_type=ConversationType.ORDER,
            )

        # Email is still an off-platform contact even in ORDER threads.
        assert outcome.warning is True
        assert outcome.code == "email"


class TestCleanMessage:
    """No violations = no side effects. Sanity check."""

    @pytest.mark.asyncio
    async def test_clean_message_passes_through_untouched(self):
        svc = _make_service()
        sender = _make_sender(violations=0)

        outcome = await svc.process_message(sender, "hey, any update on the work?")

        assert outcome.blocked is False
        assert outcome.warning is False
        assert outcome.code is None
        assert outcome.content == "hey, any update on the work?"
        assert sender.chat_violations == 0
        svc.db.add.assert_not_called()
        svc.db.flush.assert_not_called()
