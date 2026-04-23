"""Integration test — admin resolves a disputed service order with refund.

Exercises catalog_service.resolve_dispute(resolution="refund") end-to-end:
order transitions DISPUTED → CANCELLED, escrow status records refund intent
(Known Issue #2 — refund is manual today; this test only verifies the
Kaasb-side state transitions, not the actual QiCard portal transfer).

Release-path test (resolution="release") is deferred because it goes
through release_escrow_by_id which validates PaymentAccount qi_card_phone
+ qi_card_holder_name — separate test with that fixture added.
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.models.dispute import Dispute, DisputeReason, DisputeStatus
from app.models.payment import Escrow, EscrowStatus
from app.models.service import (
    Service,
    ServiceCategory,
    ServiceOrder,
    ServiceOrderStatus,
    ServicePackage,
    ServicePackageTier,
    ServiceStatus,
)
from app.models.user import User, UserRole
from app.services.catalog_service import CatalogService


@pytest_asyncio.fixture
async def sample_admin_user(db_session: AsyncSession) -> User:
    """Create an admin user (is_superuser=True)."""
    from app.core.security import hash_password

    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        username="testadmin",
        hashed_password=hash_password("AdminPass1!"),
        first_name="Test",
        last_name="Admin",
        primary_role=UserRole.ADMIN,
        is_superuser=True,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def sample_category(db_session: AsyncSession) -> ServiceCategory:
    cat = ServiceCategory(
        id=uuid.uuid4(),
        name_en="Programming",
        name_ar="برمجة",
        slug=f"programming-{uuid.uuid4().hex[:6]}",
        icon="code",
        sort_order=1,
        is_active=True,
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


@pytest_asyncio.fixture
async def disputed_order_with_frozen_escrow(
    db_session: AsyncSession,
    sample_client_user: User,
    sample_freelancer_user: User,
    sample_category: ServiceCategory,
) -> tuple[ServiceOrder, Escrow, Dispute]:
    """Order in DISPUTED state + escrow DISPUTED (frozen) + Dispute record OPEN."""
    service = Service(
        id=uuid.uuid4(),
        freelancer_id=sample_freelancer_user.id,
        category_id=sample_category.id,
        title="I will design a logo for your business",
        description="Professional logo design with unlimited revisions.",
        slug=f"logo-design-{uuid.uuid4().hex[:6]}",
        status=ServiceStatus.ACTIVE,
    )
    package = ServicePackage(
        id=uuid.uuid4(),
        service_id=service.id,
        tier=ServicePackageTier.BASIC,
        name="Logo Basic",
        description="One concept, two revisions, delivered as PNG.",
        price=Decimal("50000"),
        delivery_days=2,
        revisions=2,
    )
    db_session.add_all([service, package])
    await db_session.flush()

    order = ServiceOrder(
        id=uuid.uuid4(),
        service_id=service.id,
        package_id=package.id,
        client_id=sample_client_user.id,
        freelancer_id=sample_freelancer_user.id,
        status=ServiceOrderStatus.DISPUTED,
        price_paid=50000.0,
        delivery_days=2,
        revisions_remaining=2,
    )
    db_session.add(order)
    await db_session.flush()

    escrow = Escrow(
        id=uuid.uuid4(),
        service_order_id=order.id,
        client_id=sample_client_user.id,
        freelancer_id=sample_freelancer_user.id,
        status=EscrowStatus.DISPUTED,
        amount=Decimal("50000.00"),
        platform_fee=Decimal("5000.00"),
        freelancer_amount=Decimal("45000.00"),
        currency="IQD",
        version=1,
    )
    db_session.add(escrow)
    await db_session.flush()

    dispute = Dispute(
        id=uuid.uuid4(),
        order_id=order.id,
        initiated_by="client",
        reason=DisputeReason.NOT_AS_DESCRIBED,
        description="The delivery doesn't match what was promised in the service description.",
        status=DisputeStatus.OPEN,
    )
    db_session.add(dispute)
    await db_session.flush()

    return order, escrow, dispute


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_admin_resolves_dispute_with_refund(
    db_session: AsyncSession,
    sample_admin_user: User,
    disputed_order_with_frozen_escrow: tuple[ServiceOrder, Escrow, Dispute],
):
    """Admin resolves with resolution='refund' → order CANCELLED + refund queued."""
    order, escrow, _ = disputed_order_with_frozen_escrow
    svc = CatalogService(db_session)

    resolved_order = await svc.resolve_dispute(
        order_id=order.id,
        admin=sample_admin_user,
        resolution="refund",
        admin_note="Client demonstrated scope mismatch with screenshots.",
    )

    # Order transitioned to CANCELLED
    assert resolved_order.status == ServiceOrderStatus.CANCELLED
    assert resolved_order.dispute_resolution == "refunded_to_client"
    assert resolved_order.dispute_resolved_at is not None
    assert str(resolved_order.cancelled_by) == str(sample_admin_user.id)
    # admin_note should be included in the cancellation_reason
    assert "scope mismatch" in (resolved_order.cancellation_reason or "")

    # Escrow left the DISPUTED state — exact end-state depends on
    # refund_escrow_by_service_order behaviour (flips to PROCESSING /
    # REFUNDED depending on QiCard v0 API being available). Refresh and
    # assert it is no longer DISPUTED.
    await db_session.refresh(escrow)
    assert escrow.status != EscrowStatus.DISPUTED


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_resolve_rejects_invalid_resolution_string(
    db_session: AsyncSession,
    sample_admin_user: User,
    disputed_order_with_frozen_escrow: tuple[ServiceOrder, Escrow, Dispute],
):
    """Only 'release' or 'refund' accepted — anything else raises."""
    order, _, _ = disputed_order_with_frozen_escrow
    svc = CatalogService(db_session)

    with pytest.raises(BadRequestError) as exc:
        await svc.resolve_dispute(
            order_id=order.id,
            admin=sample_admin_user,
            resolution="partial_split",  # not supported
        )
    assert "release" in str(exc.value).lower() or "refund" in str(exc.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_resolve_rejects_non_disputed_order(
    db_session: AsyncSession,
    sample_admin_user: User,
    disputed_order_with_frozen_escrow: tuple[ServiceOrder, Escrow, Dispute],
):
    """Order must be in DISPUTED state to resolve a dispute."""
    order, _, _ = disputed_order_with_frozen_escrow
    order.status = ServiceOrderStatus.IN_PROGRESS  # flip out of DISPUTED
    await db_session.flush()

    svc = CatalogService(db_session)
    with pytest.raises(BadRequestError) as exc:
        await svc.resolve_dispute(
            order_id=order.id,
            admin=sample_admin_user,
            resolution="refund",
        )
    assert "disputed" in str(exc.value).lower()
