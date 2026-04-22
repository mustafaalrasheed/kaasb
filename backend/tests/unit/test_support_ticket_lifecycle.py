"""
Unit tests for the support-ticket lifecycle on ``MessageService``.

Covers the three explicit state transitions (claim / resolve / reopen)
plus the guards — only SUPPORT conversations accept lifecycle calls,
and only staff can make them. DB is mocked so ``_get_conversation``
returns a pre-built Conversation stub without touching Postgres.

The user-reply auto-reopen hook inside ``_send_message`` has many DB
dependencies and is better covered by an integration test; we lock in
just the state-machine part here.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from app.core.exceptions import BadRequestError, ForbiddenError
from app.models.message import ConversationType, SupportTicketStatus
from app.models.user import UserRole, UserStatus


@pytest_asyncio.fixture(autouse=True)
async def _skip_real_db():
    """Bypass conftest's Postgres fixture — mocks only."""
    yield


def _make_user(
    *,
    is_superuser: bool = False,
    is_support: bool = False,
    role: UserRole = UserRole.CLIENT,
):
    from app.models.user import User

    u = User()
    u.id = uuid.uuid4()
    u.username = f"u-{u.id.hex[:6]}"
    u.email = f"{u.username}@test.com"
    u.first_name = "Test"
    u.last_name = "User"
    u.primary_role = role
    u.status = UserStatus.ACTIVE
    u.is_superuser = is_superuser
    u.is_support = is_support
    return u


def _make_conversation(
    *,
    conv_type: ConversationType = ConversationType.SUPPORT,
    status: SupportTicketStatus | None = SupportTicketStatus.OPEN,
    assignee_id: uuid.UUID | None = None,
):
    from app.models.message import Conversation

    c = Conversation()
    c.id = uuid.uuid4()
    c.conversation_type = conv_type
    c.support_status = status
    c.support_assignee_id = assignee_id
    c.support_assignee = None
    c.support_resolved_at = None
    return c


def _make_service(conversation):
    """Build a MessageService with _get_conversation wired to return `conversation`."""
    from app.services.message_service import MessageService

    svc = MessageService.__new__(MessageService)
    svc.db = MagicMock()
    svc.db.flush = AsyncMock(return_value=None)

    # Stub the SELECT inside _get_conversation: scalar_one_or_none → conversation.
    exec_result = MagicMock()
    exec_result.scalar_one_or_none = MagicMock(return_value=conversation)
    svc.db.execute = AsyncMock(return_value=exec_result)
    return svc


# ── claim ─────────────────────────────────────────────────────────────────────

class TestClaimSupportTicket:
    @pytest.mark.asyncio
    async def test_admin_claims_open_ticket(self):
        conv = _make_conversation(status=SupportTicketStatus.OPEN)
        svc = _make_service(conv)
        admin = _make_user(is_superuser=True)

        result = await svc.claim_support_ticket(conv.id, admin)

        assert result.support_status == SupportTicketStatus.IN_PROGRESS
        assert result.support_assignee_id == admin.id
        assert result.support_assignee is admin  # relationship populated
        assert result.support_resolved_at is None
        svc.db.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_support_role_can_claim(self):
        # is_support=True (not admin) should still pass the _is_staff gate.
        conv = _make_conversation(status=SupportTicketStatus.OPEN)
        svc = _make_service(conv)
        staff = _make_user(is_support=True)

        result = await svc.claim_support_ticket(conv.id, staff)

        assert result.support_status == SupportTicketStatus.IN_PROGRESS
        assert result.support_assignee_id == staff.id

    @pytest.mark.asyncio
    async def test_claim_transfers_ownership(self):
        # If another staff already claimed it, a new claim overwrites the
        # assignee — useful for handoffs.
        prior_assignee_id = uuid.uuid4()
        conv = _make_conversation(
            status=SupportTicketStatus.IN_PROGRESS,
            assignee_id=prior_assignee_id,
        )
        svc = _make_service(conv)
        staff = _make_user(is_superuser=True)

        result = await svc.claim_support_ticket(conv.id, staff)

        assert result.support_assignee_id == staff.id
        assert result.support_assignee_id != prior_assignee_id

    @pytest.mark.asyncio
    async def test_non_staff_forbidden(self):
        conv = _make_conversation()
        svc = _make_service(conv)
        client = _make_user(role=UserRole.CLIENT)

        with pytest.raises(ForbiddenError):
            await svc.claim_support_ticket(conv.id, client)

    @pytest.mark.asyncio
    async def test_wrong_conversation_type_bad_request(self):
        # Can't claim a regular user↔user DM as a support ticket.
        conv = _make_conversation(
            conv_type=ConversationType.USER,
            status=None,
        )
        svc = _make_service(conv)
        admin = _make_user(is_superuser=True)

        with pytest.raises(BadRequestError):
            await svc.claim_support_ticket(conv.id, admin)


# ── resolve ───────────────────────────────────────────────────────────────────

class TestResolveSupportTicket:
    @pytest.mark.asyncio
    async def test_resolve_sets_status_and_timestamp(self):
        staff_id = uuid.uuid4()
        conv = _make_conversation(
            status=SupportTicketStatus.IN_PROGRESS,
            assignee_id=staff_id,
        )
        svc = _make_service(conv)
        staff = _make_user(is_superuser=True)
        staff.id = staff_id  # same staff resolving what they claimed

        before = datetime.now(UTC)
        result = await svc.resolve_support_ticket(conv.id, staff)

        assert result.support_status == SupportTicketStatus.RESOLVED
        assert result.support_resolved_at is not None
        assert result.support_resolved_at >= before
        # Assignee preserved — history shows who handled it.
        assert result.support_assignee_id == staff_id

    @pytest.mark.asyncio
    async def test_resolve_unclaimed_takes_ownership(self):
        # Resolving an OPEN, unassigned ticket sets the resolving staff
        # as the assignee so the audit trail is complete.
        conv = _make_conversation(
            status=SupportTicketStatus.OPEN,
            assignee_id=None,
        )
        svc = _make_service(conv)
        staff = _make_user(is_superuser=True)

        result = await svc.resolve_support_ticket(conv.id, staff)

        assert result.support_status == SupportTicketStatus.RESOLVED
        assert result.support_assignee_id == staff.id
        assert result.support_assignee is staff

    @pytest.mark.asyncio
    async def test_resolve_does_not_override_existing_assignee(self):
        # If someone else claimed it, resolve keeps their ownership intact
        # (unlike claim, which transfers).
        original_assignee = uuid.uuid4()
        conv = _make_conversation(
            status=SupportTicketStatus.IN_PROGRESS,
            assignee_id=original_assignee,
        )
        svc = _make_service(conv)
        different_staff = _make_user(is_superuser=True)

        result = await svc.resolve_support_ticket(conv.id, different_staff)

        assert result.support_assignee_id == original_assignee

    @pytest.mark.asyncio
    async def test_non_staff_forbidden(self):
        conv = _make_conversation()
        svc = _make_service(conv)
        freelancer = _make_user(role=UserRole.FREELANCER)

        with pytest.raises(ForbiddenError):
            await svc.resolve_support_ticket(conv.id, freelancer)


# ── reopen ────────────────────────────────────────────────────────────────────

class TestReopenSupportTicket:
    @pytest.mark.asyncio
    async def test_reopen_clears_resolved_at(self):
        conv = _make_conversation(status=SupportTicketStatus.RESOLVED)
        conv.support_resolved_at = datetime.now(UTC)
        svc = _make_service(conv)
        staff = _make_user(is_superuser=True)

        result = await svc.reopen_support_ticket(conv.id, staff)

        assert result.support_status == SupportTicketStatus.OPEN
        assert result.support_resolved_at is None

    @pytest.mark.asyncio
    async def test_non_staff_forbidden(self):
        conv = _make_conversation(status=SupportTicketStatus.RESOLVED)
        svc = _make_service(conv)
        client = _make_user(role=UserRole.CLIENT)

        with pytest.raises(ForbiddenError):
            await svc.reopen_support_ticket(conv.id, client)

    @pytest.mark.asyncio
    async def test_wrong_conversation_type_bad_request(self):
        conv = _make_conversation(conv_type=ConversationType.ORDER, status=None)
        svc = _make_service(conv)
        staff = _make_user(is_superuser=True)

        with pytest.raises(BadRequestError):
            await svc.reopen_support_ticket(conv.id, staff)


# ── _is_staff predicate ──────────────────────────────────────────────────────

class TestIsStaffPredicate:
    """_is_staff gates every lifecycle call. Lock in its truth table."""

    def test_admin_is_staff(self):
        from app.services.message_service import _is_staff
        assert _is_staff(_make_user(is_superuser=True)) is True

    def test_support_is_staff(self):
        from app.services.message_service import _is_staff
        assert _is_staff(_make_user(is_support=True)) is True

    def test_admin_with_support_is_staff(self):
        from app.services.message_service import _is_staff
        assert _is_staff(_make_user(is_superuser=True, is_support=True)) is True

    def test_client_not_staff(self):
        from app.services.message_service import _is_staff
        assert _is_staff(_make_user(role=UserRole.CLIENT)) is False

    def test_freelancer_not_staff(self):
        from app.services.message_service import _is_staff
        assert _is_staff(_make_user(role=UserRole.FREELANCER)) is False


# ── SupportTicketStatus enum values ──────────────────────────────────────────

class TestSupportTicketStatusValues:
    """Frontend depends on these string values — lock them in."""

    def test_open_value(self):
        assert SupportTicketStatus.OPEN.value == "open"

    def test_in_progress_value(self):
        assert SupportTicketStatus.IN_PROGRESS.value == "in_progress"

    def test_resolved_value(self):
        assert SupportTicketStatus.RESOLVED.value == "resolved"
