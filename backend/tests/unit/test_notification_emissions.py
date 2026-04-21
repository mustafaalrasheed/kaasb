"""Unit tests for PR-N1 notification emission coverage.

Each new NotificationType emission is tested at the source level — the test
asserts that the enum value is referenced from the expected service module.
This catches the common regression of a service refactor silently removing a
`notify(...)` call, without requiring a full DB fixture to drive each
emission path end-to-end.
"""

import ast
import pathlib

import pytest
import pytest_asyncio

from app.models.notification import NotificationType


# The pure-unit tests in this file do not touch the database.
@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    yield


BACKEND = pathlib.Path(__file__).resolve().parents[2] / "app"


def _references_enum_value(path: pathlib.Path, value: NotificationType) -> bool:
    """True when the source file contains a `NotificationType.<NAME>` reference."""
    if not path.exists():
        return False
    tree = ast.parse(path.read_text())
    target_name = value.name  # e.g. "MILESTONE_FUNDED"
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == target_name
            and isinstance(node.value, ast.Name)
            and node.value.id == "NotificationType"
        ):
            return True
    return False


@pytest.mark.parametrize(
    ("service_rel_path", "notification_type"),
    [
        ("services/payment_service.py", NotificationType.MILESTONE_FUNDED),
        ("services/contract_service.py", NotificationType.MILESTONE_SUBMITTED),
        ("services/contract_service.py", NotificationType.MILESTONE_APPROVED),
        ("services/contract_service.py", NotificationType.MILESTONE_REVISION),
        ("services/review_service.py", NotificationType.REVIEW_RECEIVED),
        ("tasks/marketplace_tasks.py", NotificationType.SELLER_LEVEL_UPGRADED),
        # These are not new in PR-N1 but were flagged in the audit; lock them
        # in as well so a future refactor can't silently drop them.
        ("services/buyer_request_service.py", NotificationType.BUYER_REQUEST_OFFER_REJECTED),
        ("services/gig_service.py", NotificationType.DISPUTE_RESOLVED),
        ("services/message_subscribers.py", NotificationType.NEW_MESSAGE),
        ("services/payment_service.py", NotificationType.PAYOUT_COMPLETED),
    ],
)
def test_notification_emission_present(service_rel_path, notification_type):
    """The expected NotificationType must be referenced from the right module.

    Catches refactors that silently drop a `notify(...)` call. Doesn't verify
    that the emission path is reachable at runtime — that's integration test
    territory — but eliminates the silent-removal failure mode, which is the
    common one.
    """
    path = BACKEND / service_rel_path
    assert _references_enum_value(path, notification_type), (
        f"{service_rel_path} must reference NotificationType.{notification_type.name}"
    )


class TestSellerLevelUpgradeOnlyNotifiesUpgrades:
    """The upgraded/downgraded branch in recalculate_seller_levels must ONLY
    fire a notification for upgraded users — demotions are silent."""

    def test_only_upgraded_users_are_queued(self):
        src = (BACKEND / "tasks" / "marketplace_tasks.py").read_text()
        # The task accumulates upgraded users in `upgraded_users` and only
        # loops that list for notifications. Grepping for the only source of
        # the notify call is a strong regression guard.
        assert "upgraded_users.append" in src
        # There must be exactly one notify_background call tied to the enum.
        assert src.count("NotificationType.SELLER_LEVEL_UPGRADED") == 1


class TestSchemaIsEnumTyped:
    """NotificationDetail.type must be the NotificationType enum, not bare str.

    Without this, a typo in a new service-layer `notify(type=...)` call would
    be silently serialized as a string and reach the frontend unvalidated.
    """

    def test_schema_type_field_is_enum(self):
        from app.schemas.notification import NotificationDetail

        fields = NotificationDetail.model_fields
        assert fields["type"].annotation is NotificationType
