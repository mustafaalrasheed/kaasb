"""Integration test — escrow release when client completes a service order.

Covers the core revenue path: freelancer delivers → client accepts → escrow
flips FUNDED → RELEASED and the platform fee + freelancer-amount ledger
transactions are written. Exercises catalog_service.complete_order +
payment_service._release_locked_escrow end-to-end against real Postgres.

Does NOT exercise the inbound Qi Card webhook path (that's a separate test).
Here we pre-seed the escrow in FUNDED state — matching the post-webhook
world — and focus on the release half of the lifecycle.
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError
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
from app.models.user import User
from app.services.catalog_service import CatalogService


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
async def delivered_order_with_funded_escrow(
    db_session: AsyncSession,
    sample_client_user: User,
    sample_freelancer_user: User,
    sample_category: ServiceCategory,
) -> tuple[ServiceOrder, Escrow]:
    """An order already in DELIVERED state with its escrow FUNDED.

    This is the precondition for complete_order: matches the world where
    payment confirmed + freelancer submitted delivery.
    """
    service = Service(
        id=uuid.uuid4(),
        freelancer_id=sample_freelancer_user.id,
        category_id=sample_category.id,
        title="I will debug your Python backend",
        description="Systematic bug-hunting with reproducible fixes.",
        slug=f"debug-python-{uuid.uuid4().hex[:6]}",
        status=ServiceStatus.ACTIVE,
    )
    package = ServicePackage(
        id=uuid.uuid4(),
        service_id=service.id,
        tier=ServicePackageTier.BASIC,
        name="One Bug",
        description="Fix one reproducible bug in your codebase.",
        price=Decimal("100000"),
        delivery_days=3,
        revisions=1,
    )
    db_session.add_all([service, package])
    await db_session.flush()

    order = ServiceOrder(
        id=uuid.uuid4(),
        service_id=service.id,
        package_id=package.id,
        client_id=sample_client_user.id,
        freelancer_id=sample_freelancer_user.id,
        status=ServiceOrderStatus.DELIVERED,
        price_paid=100000.0,
        delivery_days=3,
        revisions_remaining=1,
    )
    db_session.add(order)
    await db_session.flush()

    # Escrow FUNDED and linked to the order. Platform fee 10%.
    escrow = Escrow(
        id=uuid.uuid4(),
        service_order_id=order.id,
        client_id=sample_client_user.id,
        freelancer_id=sample_freelancer_user.id,
        status=EscrowStatus.FUNDED,
        amount=Decimal("100000.00"),
        platform_fee=Decimal("10000.00"),
        freelancer_amount=Decimal("90000.00"),
        currency="IQD",
        version=1,
    )
    db_session.add(escrow)
    await db_session.flush()

    return order, escrow


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_complete_order_releases_funded_escrow(
    db_session: AsyncSession,
    sample_client_user: User,
    delivered_order_with_funded_escrow: tuple[ServiceOrder, Escrow],
):
    """Client accepts a DELIVERED order → order COMPLETED + escrow RELEASED."""
    order, escrow = delivered_order_with_funded_escrow
    svc = CatalogService(db_session)

    completed = await svc.complete_order(order.id, sample_client_user)

    # Order transitions cleanly
    assert completed.status == ServiceOrderStatus.COMPLETED
    assert completed.completed_at is not None

    # Escrow released — fetch fresh because complete_order commits its
    # own transaction internally and the in-memory instance may be stale.
    await db_session.refresh(escrow)
    assert escrow.status == EscrowStatus.RELEASED
    assert escrow.released_at is not None
    assert escrow.version == 2  # optimistic-lock increment from version=1 fixture


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_complete_order_rejects_non_delivered_state(
    db_session: AsyncSession,
    sample_client_user: User,
    delivered_order_with_funded_escrow: tuple[ServiceOrder, Escrow],
):
    """Order must be in DELIVERED state — IN_PROGRESS raises BadRequestError."""
    order, _ = delivered_order_with_funded_escrow
    order.status = ServiceOrderStatus.IN_PROGRESS
    await db_session.flush()

    svc = CatalogService(db_session)
    with pytest.raises(BadRequestError) as exc:
        await svc.complete_order(order.id, sample_client_user)
    assert "delivered" in str(exc.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_complete_order_rejects_non_owner(
    db_session: AsyncSession,
    sample_freelancer_user: User,
    delivered_order_with_funded_escrow: tuple[ServiceOrder, Escrow],
):
    """Only the order's client can complete it — the freelancer cannot."""
    order, _ = delivered_order_with_funded_escrow

    svc = CatalogService(db_session)
    with pytest.raises(ForbiddenError):
        await svc.complete_order(order.id, sample_freelancer_user)
