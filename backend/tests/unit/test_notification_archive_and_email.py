"""Unit tests for PR-N4:
- notifications.archived_at is filtered from active queries
- Retention task archives instead of hard-deletes
- Email copy fires only for whitelisted types, only when user opted in
- _build_link_url composes frontend URLs correctly
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


def _make_session_with_user(
    locale: str = "ar",
    email: str | None = None,
    email_pref: bool = True,
):
    """Minimal mock session whose first execute() returns locale, second
    returns (email, email_pref) — matches the order _resolve_locale then
    _resolve_email_context call on the create_notification path."""
    session = MagicMock()

    locale_scalar = MagicMock()
    locale_scalar.scalar_one_or_none = MagicMock(return_value=locale)
    email_result = MagicMock()
    email_result.first = MagicMock(
        return_value=(email, email_pref) if email else None
    )
    session.execute = AsyncMock(side_effect=[locale_scalar, email_result])

    added: list = []
    session.add = MagicMock(side_effect=lambda obj: added.append(obj))

    async def _flush():
        for obj in added:
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(UTC)
    session.flush = AsyncMock(side_effect=_flush)
    return session


class TestBuildLinkUrl:
    """_build_link_url composes an absolute URL based on FRONTEND_URL."""

    def test_contract_link(self):
        from app.services.notification_service import _build_link_url

        with patch(
            "app.services.notification_service.get_settings"
        ) as settings_mock:
            settings_mock.return_value.FRONTEND_URL = "https://kaasb.com"
            contract_id = uuid.uuid4()
            url = _build_link_url("contract", contract_id)
            assert url == f"https://kaasb.com/dashboard/contracts/{contract_id}"

    def test_gig_order_link_has_query(self):
        from app.services.notification_service import _build_link_url

        with patch("app.services.notification_service.get_settings") as s:
            s.return_value.FRONTEND_URL = "https://kaasb.com/"
            order_id = uuid.uuid4()
            url = _build_link_url("gig_order", order_id)
            assert url == f"https://kaasb.com/dashboard/gigs/orders?order={order_id}"

    def test_unknown_link_type_returns_none(self):
        from app.services.notification_service import _build_link_url

        with patch("app.services.notification_service.get_settings") as s:
            s.return_value.FRONTEND_URL = "https://kaasb.com"
            assert _build_link_url("does-not-exist", uuid.uuid4()) is None

    def test_none_link_type_returns_none(self):
        from app.services.notification_service import _build_link_url
        assert _build_link_url(None, None) is None


class TestEmailGating:
    """create_notification fires send_notification_email only for whitelisted
    types AND only when the recipient has email_notifications_enabled."""

    @pytest.mark.asyncio
    async def test_whitelisted_type_with_opt_in_sends_email(self):
        from app.models.notification import NotificationType
        from app.services.notification_service import NotificationService

        session = _make_session_with_user(
            locale="en", email="user@example.com", email_pref=True
        )
        svc = NotificationService(session)

        with patch(
            "app.services.notification_service.manager"
        ) as mgr, patch(
            "app.services.notification_service._send_notification_email_bg",
            new_callable=AsyncMock,
        ) as email_mock, patch(
            "app.services.notification_service.asyncio.create_task",
            side_effect=lambda coro: coro,  # just return the coroutine
        ):
            mgr.send_to_user = AsyncMock(return_value=None)
            await svc.create_notification(
                user_id=uuid.uuid4(),
                type=NotificationType.PAYMENT_RECEIVED,
                title_ar="عربي", title_en="English",
                message_ar="AR", message_en="EN",
                link_type="contract", link_id=uuid.uuid4(),
            )

        # Email helper must have been scheduled. asyncio.create_task is mocked
        # to return the coroutine, so we await it to trigger the patched body.
        email_mock.assert_called_once()
        call_kwargs = email_mock.call_args.kwargs
        assert call_kwargs["email"] == "user@example.com"
        assert call_kwargs["title"] == "English"
        assert call_kwargs["lang"] == "en"
        # Link URL composed from FRONTEND_URL (default http://localhost:3000).
        assert "/dashboard/contracts/" in call_kwargs["link_url"]

    @pytest.mark.asyncio
    async def test_whitelisted_type_with_opt_out_skips_email(self):
        from app.models.notification import NotificationType
        from app.services.notification_service import NotificationService

        session = _make_session_with_user(
            locale="ar", email="user@example.com", email_pref=False
        )
        svc = NotificationService(session)

        with patch(
            "app.services.notification_service.manager"
        ) as mgr, patch(
            "app.services.notification_service._send_notification_email_bg",
            new_callable=AsyncMock,
        ) as email_mock, patch(
            "app.services.notification_service.asyncio.create_task",
        ):
            mgr.send_to_user = AsyncMock(return_value=None)
            await svc.create_notification(
                user_id=uuid.uuid4(),
                type=NotificationType.PAYMENT_RECEIVED,
                title_ar="عربي", title_en="English",
                message_ar="AR", message_en="EN",
            )

        email_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_whitelisted_type_never_emails(self):
        from app.models.notification import NotificationType
        from app.services.notification_service import NotificationService

        # Even with email_pref=True and a valid address, a non-whitelisted
        # type (e.g. PROPOSAL_SHORTLISTED) must not trigger an email.
        session = MagicMock()
        locale_scalar = MagicMock()
        locale_scalar.scalar_one_or_none = MagicMock(return_value="ar")
        # Only one execute call is expected when the type is not emailable —
        # we never reach _resolve_email_context.
        session.execute = AsyncMock(return_value=locale_scalar)
        added: list = []
        session.add = MagicMock(side_effect=lambda obj: added.append(obj))

        async def _flush():
            for obj in added:
                if getattr(obj, "created_at", None) is None:
                    obj.created_at = datetime.now(UTC)
        session.flush = AsyncMock(side_effect=_flush)

        svc = NotificationService(session)

        with patch(
            "app.services.notification_service.manager"
        ) as mgr, patch(
            "app.services.notification_service._send_notification_email_bg",
            new_callable=AsyncMock,
        ) as email_mock, patch(
            "app.services.notification_service.asyncio.create_task",
        ):
            mgr.send_to_user = AsyncMock(return_value=None)
            await svc.create_notification(
                user_id=uuid.uuid4(),
                type=NotificationType.PROPOSAL_SHORTLISTED,  # not in whitelist
                title_ar="x", title_en="x",
                message_ar="x", message_en="x",
            )

        email_mock.assert_not_called()


class TestArchivedAtFilter:
    """get_unread_count and get_notifications skip archived rows."""

    @pytest.mark.asyncio
    async def test_unread_count_filters_archived(self):
        from app.services.notification_service import NotificationService

        session = MagicMock()
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=7)
        session.execute = AsyncMock(return_value=count_result)

        svc = NotificationService(session)
        user = MagicMock()
        user.id = uuid.uuid4()

        n = await svc.get_unread_count(user)
        assert n == 7
        # The SQL sent to execute must reference archived_at.
        call_stmt = str(session.execute.await_args.args[0])
        assert "archived_at" in call_stmt


class TestRetentionArchives:
    """The data retention task writes archived_at instead of DELETE."""

    def test_retention_sql_uses_update(self):
        # Static check: data_retention.py must issue UPDATE, not DELETE, for
        # notifications. Catches a regression that silently reintroduces
        # hard-delete and loses GDPR-exportable history.
        import pathlib
        src = pathlib.Path(
            pathlib.Path(__file__).resolve().parents[2]
            / "app" / "tasks" / "data_retention.py"
        ).read_text()
        assert "UPDATE notifications SET archived_at" in src
        assert "DELETE FROM notifications" not in src


class TestUserHasEmailPrefColumn:
    def test_column_exists_and_defaults_true(self):
        from app.models.user import User

        col = User.__table__.columns["email_notifications_enabled"]
        assert not col.nullable
        # server_default is a TextClause wrapping "true".
        assert "true" in str(col.server_default.arg).lower()
