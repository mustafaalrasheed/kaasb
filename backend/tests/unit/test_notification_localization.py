"""Unit tests for PR-N2 notification localization.

- NotificationService.create_notification resolves the recipient's locale
  and persists the matching copy.
- notify() and notify_background() signatures require both AR/EN pairs.
- Every service emission call site passes both title_ar AND title_en (and
  message_ar AND message_en). A regression in any call site would reintroduce
  the "English users see Arabic" bug from the audit.
"""

import ast
import inspect
import pathlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.models.notification import NotificationType


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


BACKEND = pathlib.Path(__file__).resolve().parents[2] / "app"


def _make_session(locale_value):
    """Build a mock AsyncSession that returns `locale_value` from the locale
    SELECT, and populates `created_at` on added rows so the service's WS
    payload construction doesn't explode on a None timestamp.
    """
    session = MagicMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none = MagicMock(return_value=locale_value)
    session.execute = AsyncMock(return_value=scalar_result)

    added: list = []
    session.add = MagicMock(side_effect=lambda obj: added.append(obj))

    async def _flush():
        for obj in added:
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(UTC)
    session.flush = AsyncMock(side_effect=_flush)
    return session


class TestLocaleResolution:
    """NotificationService._resolve_locale logic + create_notification routing."""

    @pytest.mark.asyncio
    async def test_english_user_gets_english_copy(self):
        from app.services.notification_service import NotificationService

        svc = NotificationService(_make_session("en"))

        with patch("app.services.notification_service.manager") as mgr:
            # manager.send_to_user() must be awaitable so asyncio.create_task
            # accepts it — MagicMock returns a MagicMock by default.
            mgr.send_to_user = AsyncMock(return_value=None)
            notif = await svc.create_notification(
                user_id=uuid.uuid4(),
                type=NotificationType.PAYMENT_RECEIVED,
                title_ar="تم استلام دفعة",
                title_en="Payment received",
                message_ar="تم تحرير 100,000 د.ع",
                message_en="100,000 IQD released",
            )

        assert notif.title == "Payment received"
        assert notif.message == "100,000 IQD released"

    @pytest.mark.asyncio
    async def test_arabic_user_gets_arabic_copy(self):
        from app.services.notification_service import NotificationService

        svc = NotificationService(_make_session("ar"))

        with patch("app.services.notification_service.manager") as mgr:
            # manager.send_to_user() must be awaitable so asyncio.create_task
            # accepts it — MagicMock returns a MagicMock by default.
            mgr.send_to_user = AsyncMock(return_value=None)
            notif = await svc.create_notification(
                user_id=uuid.uuid4(),
                type=NotificationType.PAYMENT_RECEIVED,
                title_ar="تم استلام دفعة",
                title_en="Payment received",
                message_ar="تم تحرير 100,000 د.ع",
                message_en="100,000 IQD released",
            )

        assert notif.title == "تم استلام دفعة"
        assert notif.message == "تم تحرير 100,000 د.ع"

    @pytest.mark.asyncio
    async def test_unknown_locale_falls_back_to_arabic(self):
        from app.services.notification_service import NotificationService

        # A future DB where someone wrote "fr" (unsupported) must not crash —
        # the service falls back to Arabic, the platform default.
        svc = NotificationService(_make_session("fr"))

        with patch("app.services.notification_service.manager") as mgr:
            # manager.send_to_user() must be awaitable so asyncio.create_task
            # accepts it — MagicMock returns a MagicMock by default.
            mgr.send_to_user = AsyncMock(return_value=None)
            notif = await svc.create_notification(
                user_id=uuid.uuid4(),
                type=NotificationType.PAYMENT_RECEIVED,
                title_ar="عربي",
                title_en="english",
                message_ar="AR",
                message_en="EN",
            )

        assert notif.title == "عربي"

    @pytest.mark.asyncio
    async def test_missing_user_falls_back_to_arabic(self):
        from app.services.notification_service import NotificationService

        svc = NotificationService(_make_session(None))

        with patch("app.services.notification_service.manager") as mgr:
            # manager.send_to_user() must be awaitable so asyncio.create_task
            # accepts it — MagicMock returns a MagicMock by default.
            mgr.send_to_user = AsyncMock(return_value=None)
            notif = await svc.create_notification(
                user_id=uuid.uuid4(),
                type=NotificationType.PAYMENT_RECEIVED,
                title_ar="عربي",
                title_en="english",
                message_ar="AR",
                message_en="EN",
            )

        assert notif.title == "عربي"

    @pytest.mark.asyncio
    async def test_db_error_during_locale_lookup_falls_back_to_arabic(self):
        from app.services.notification_service import NotificationService

        # Custom session where execute raises — exercises the exception path
        # in _resolve_locale without breaking the insert flow afterwards.
        session = _make_session("ar")
        session.execute = AsyncMock(side_effect=RuntimeError("db dead"))
        svc = NotificationService(session)

        with patch("app.services.notification_service.manager") as mgr:
            # manager.send_to_user() must be awaitable so asyncio.create_task
            # accepts it — MagicMock returns a MagicMock by default.
            mgr.send_to_user = AsyncMock(return_value=None)
            notif = await svc.create_notification(
                user_id=uuid.uuid4(),
                type=NotificationType.PAYMENT_RECEIVED,
                title_ar="عربي",
                title_en="english",
                message_ar="AR",
                message_en="EN",
            )

        assert notif.title == "عربي"


class TestNotifySignaturesAreBilingual:
    """The public notify() and notify_background() helpers must require all four
    locale-specific kwargs — a caller accidentally omitting title_en would be a
    regression of the P1 "English users see Arabic" bug."""

    def test_notify_signature_requires_ar_and_en(self):
        from app.services.notification_service import notify

        params = inspect.signature(notify).parameters
        for required in ("title_ar", "title_en", "message_ar", "message_en"):
            assert required in params, f"notify() missing {required}"
            assert (
                params[required].default is inspect.Parameter.empty
            ), f"notify() {required} must be required"

    def test_notify_background_signature_requires_ar_and_en(self):
        from app.services.notification_service import notify_background

        params = inspect.signature(notify_background).parameters
        for required in ("title_ar", "title_en", "message_ar", "message_en"):
            assert required in params, f"notify_background() missing {required}"
            assert (
                params[required].default is inspect.Parameter.empty
            ), f"notify_background() {required} must be required"


class TestEveryCallSitePassesBothLocales:
    """Static scan of every service module for `notify(` / `notify_background(`
    calls. Each must pass title_ar AND title_en AND message_ar AND message_en —
    otherwise Pydantic will raise at runtime and the notification is dropped.
    """

    SERVICE_FILES = [
        "services/proposal_service.py",
        "services/contract_service.py",
        "services/payment_service.py",
        "services/review_service.py",
        "services/gig_service.py",
        "services/buyer_request_service.py",
        "services/dispute_service.py",
        "services/message_filter_service.py",
        "services/message_subscribers.py",
        "tasks/marketplace_tasks.py",
    ]

    REQUIRED_KWARGS = {"title_ar", "title_en", "message_ar", "message_en"}

    def _collect_notify_calls(self, path: pathlib.Path):
        """Yield every notify / notify_background / create_notification call."""
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in {"notify", "notify_background", "create_notification"}:
                # Skip zero-keyword positional calls (the helper signature
                # inside notification_service.py itself) by requiring at least
                # one kwarg — real call sites always use kwargs.
                if node.keywords:
                    yield node

    @pytest.mark.parametrize("rel_path", SERVICE_FILES)
    def test_every_emission_has_all_four_localized_kwargs(self, rel_path):
        path = BACKEND / rel_path
        if not path.exists():
            pytest.skip(f"{rel_path} missing")

        calls = list(self._collect_notify_calls(path))
        if not calls:
            pytest.skip(f"{rel_path} contains no notify() calls")

        for call in calls:
            passed = {kw.arg for kw in call.keywords if kw.arg}
            missing = self.REQUIRED_KWARGS - passed
            assert not missing, (
                f"{rel_path}:{call.lineno} notify call missing "
                f"kwargs: {sorted(missing)}"
            )


class TestUserModelHasLocale:
    """The User ORM model must expose a non-null locale column — the migration
    creates it and the NotificationService depends on it."""

    def test_locale_column_exists(self):
        from app.models.user import User

        col = User.__table__.columns["locale"]
        assert not col.nullable
        assert col.type.length == 2
