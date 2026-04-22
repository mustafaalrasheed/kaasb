"""Unit tests for PR-C2 chat scoping + rate limit + unique constraint.

Covers:
- Support inbox scoped to assigned_staff_id = me OR NULL (queue)
- claim/release lifecycle
- Rate limit call path on message send
- Conversation model declares the new unique index location + assigned_staff_id column
"""

import ast
import pathlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


BACKEND = pathlib.Path(__file__).resolve().parents[2] / "app"


class TestSupportInboxScoping:
    """list_support_conversations must filter on assigned_staff_id — the
    before-PR-C2 behaviour of 'every staff user sees every ticket' was
    the P1 privacy bug in the audit."""

    @pytest.mark.asyncio
    async def test_default_scope_filters_to_assigned_or_unassigned(self):
        from app.services.message_service import MessageService

        staff = MagicMock()
        staff.id = uuid.uuid4()

        session = MagicMock()
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=0)
        empty_scalars = MagicMock()
        empty_scalars.unique = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        rows_result = MagicMock()
        rows_result.scalars = MagicMock(return_value=empty_scalars)
        session.execute = AsyncMock(side_effect=[count_result, rows_result])

        svc = MessageService(session)
        await svc.list_support_conversations(staff)

        # First execute = count, second = rows. The count stmt is a
        # SELECT COUNT wrapping a subquery; the compiled SQL must include
        # the assigned_staff_id filter.
        sql = str(session.execute.await_args_list[0].args[0])
        assert "assigned_staff_id" in sql, (
            "support inbox query must filter on assigned_staff_id"
        )

    @pytest.mark.asyncio
    async def test_only_mine_excludes_unassigned(self):
        """only_mine=True must not include IS NULL rows."""
        from app.services.message_service import MessageService

        staff = MagicMock()
        staff.id = uuid.uuid4()

        session = MagicMock()
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=0)
        empty_scalars = MagicMock()
        empty_scalars.unique = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        rows_result = MagicMock()
        rows_result.scalars = MagicMock(return_value=empty_scalars)
        session.execute = AsyncMock(side_effect=[count_result, rows_result])

        svc = MessageService(session)
        await svc.list_support_conversations(staff, only_mine=True)

        # With only_mine the SQL must use equality on assigned_staff_id
        # and must not include `IS NULL` in the WHERE.
        sql = str(session.execute.await_args_list[0].args[0])
        assert "assigned_staff_id" in sql
        # only_mine=True should use equality only; no `IS NULL` fallback
        # to unassigned tickets.
        assert "IS NULL" not in sql.upper().split("WHERE")[-1] or (
            "ASSIGNED_STAFF_ID IS NULL" not in sql.upper()
        ), "only_mine=True should not include the unassigned queue"


class TestClaimRelease:
    """claim_support_conversation / release_support_conversation enforce
    the mutual-exclusion invariant between support staff."""

    @pytest.mark.asyncio
    async def test_claim_unassigned_succeeds(self):
        from app.models.message import Conversation, ConversationType
        from app.services.message_service import MessageService

        staff = MagicMock()
        staff.id = uuid.uuid4()

        conv = Conversation()
        conv.id = uuid.uuid4()
        conv.conversation_type = ConversationType.SUPPORT
        conv.assigned_staff_id = None

        session = MagicMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=conv)
        session.execute = AsyncMock(return_value=scalar_result)
        session.commit = AsyncMock(return_value=None)
        session.refresh = AsyncMock(return_value=None)

        svc = MessageService(session)
        result = await svc.claim_support_conversation(conv.id, staff)

        assert result.assigned_staff_id == staff.id

    @pytest.mark.asyncio
    async def test_claim_already_assigned_to_other_raises_conflict(self):
        from app.core.exceptions import ConflictError
        from app.models.message import Conversation, ConversationType
        from app.services.message_service import MessageService

        staff = MagicMock()
        staff.id = uuid.uuid4()

        conv = Conversation()
        conv.id = uuid.uuid4()
        conv.conversation_type = ConversationType.SUPPORT
        conv.assigned_staff_id = uuid.uuid4()  # different staff user

        session = MagicMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=conv)
        session.execute = AsyncMock(return_value=scalar_result)

        svc = MessageService(session)
        with pytest.raises(ConflictError):
            await svc.claim_support_conversation(conv.id, staff)

    @pytest.mark.asyncio
    async def test_claim_rejects_non_support_type(self):
        from app.core.exceptions import BadRequestError
        from app.models.message import Conversation, ConversationType
        from app.services.message_service import MessageService

        staff = MagicMock()
        staff.id = uuid.uuid4()

        conv = Conversation()
        conv.id = uuid.uuid4()
        conv.conversation_type = ConversationType.USER
        conv.assigned_staff_id = None

        session = MagicMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=conv)
        session.execute = AsyncMock(return_value=scalar_result)

        svc = MessageService(session)
        with pytest.raises(BadRequestError):
            await svc.claim_support_conversation(conv.id, staff)

    @pytest.mark.asyncio
    async def test_release_by_non_assignee_raises_forbidden(self):
        from app.core.exceptions import ForbiddenError
        from app.models.message import Conversation, ConversationType
        from app.services.message_service import MessageService

        staff = MagicMock()
        staff.id = uuid.uuid4()

        conv = Conversation()
        conv.id = uuid.uuid4()
        conv.conversation_type = ConversationType.SUPPORT
        conv.assigned_staff_id = uuid.uuid4()  # someone else

        session = MagicMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=conv)
        session.execute = AsyncMock(return_value=scalar_result)

        svc = MessageService(session)
        with pytest.raises(ForbiddenError):
            await svc.release_support_conversation(conv.id, staff)

    @pytest.mark.asyncio
    async def test_release_by_assignee_clears_field(self):
        from app.models.message import Conversation, ConversationType
        from app.services.message_service import MessageService

        staff = MagicMock()
        staff.id = uuid.uuid4()

        conv = Conversation()
        conv.id = uuid.uuid4()
        conv.conversation_type = ConversationType.SUPPORT
        conv.assigned_staff_id = staff.id

        session = MagicMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=conv)
        session.execute = AsyncMock(return_value=scalar_result)
        session.commit = AsyncMock(return_value=None)
        session.refresh = AsyncMock(return_value=None)

        svc = MessageService(session)
        result = await svc.release_support_conversation(conv.id, staff)
        assert result.assigned_staff_id is None


class TestMessageSendRateLimited:
    """The /messages/conversations/{id} endpoint calls into rate_limiter
    before delegating to MessageService — catches the audit's P2 DoS gap
    with a source-level presence check."""

    def test_endpoint_calls_rate_limiter(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "messages.py").read_text()
        # The rate-limit call must be ordered BEFORE the MessageService call
        # so a throttled sender can't write to the DB.
        rl_index = src.find("rate_limiter.is_allowed")
        send_index = src.find("service.send_message")
        assert rl_index != -1, "send_message endpoint is missing rate_limiter.is_allowed"
        assert send_index != -1
        assert rl_index < send_index, (
            "rate_limiter must be invoked before service.send_message"
        )

    def test_rate_limit_key_is_per_user_per_conversation(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "messages.py").read_text()
        # The key must scope by BOTH user and conversation — a single-tier
        # per-IP limit wouldn't protect a victim thread from spam by one
        # logged-in user, and a per-user-only limit would let spam spread
        # across threads.
        assert "msg_send:" in src
        assert "current_user.id" in src
        assert "conversation_id" in src


class TestConversationModelChanges:
    def test_assigned_staff_id_column_exists(self):
        from app.models.message import Conversation

        col = Conversation.__table__.columns["assigned_staff_id"]
        assert col.nullable is True
        # Column must have an index (ix_conversations_assigned_staff_id).
        idx_names = {idx.name for idx in Conversation.__table__.indexes}
        assert "ix_conversations_assigned_staff_id" in idx_names

    def test_old_job_unique_constraint_dropped(self):
        """The old UniqueConstraint(p1, p2, job_id) is gone; the real
        constraint lives in the DB as a NULLS NOT DISTINCT index created
        by migration d6y7z8a9b0c1."""
        from app.models.message import Conversation

        constraint_names = {c.name for c in Conversation.__table_args__}
        assert "uq_conversation_participants_job" not in constraint_names


class TestMigrationSqlShape:
    """Lock the migration's intent so a future regeneration can't silently
    drop the NULLS NOT DISTINCT clause (which is the whole point)."""

    def test_migration_uses_nulls_not_distinct(self):
        path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "alembic" / "versions" / "d6y7z8a9b0c1_conversations_staff_scope_and_unique.py"
        )
        src = path.read_text()
        assert "NULLS NOT DISTINCT" in src
        assert "assigned_staff_id" in src
        # And it must drop the old constraint first.
        assert "drop_constraint(" in src
        assert "uq_conversation_participants_job" in src

    def test_migration_ast_defines_upgrade_and_downgrade(self):
        """Every migration file must define both upgrade() and downgrade()
        so we can roll back."""
        path = (
            pathlib.Path(__file__).resolve().parents[2]
            / "alembic" / "versions" / "d6y7z8a9b0c1_conversations_staff_scope_and_unique.py"
        )
        tree = ast.parse(path.read_text())
        funcs = {
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        assert {"upgrade", "downgrade"}.issubset(funcs)


class TestPresenceScoping:
    """/messages/presence must filter the requested user_ids to those that
    share a conversation with the caller, unless the caller is staff."""

    def test_endpoint_source_mentions_scope_and_staff_bypass(self):
        src = (BACKEND / "api" / "v1" / "endpoints" / "messages.py").read_text()
        # Not a precise behaviour assert — a structural guard that the
        # scoping logic is present. The behavioural checks live in
        # integration tests (future).
        assert "is_superuser" in src
        assert "is_support" in src
        assert "partners_stmt" in src
        assert "allowed" in src
