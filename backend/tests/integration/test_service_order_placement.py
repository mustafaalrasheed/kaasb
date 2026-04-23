"""Integration test — ServiceOrder placement against real Postgres.

Exercises the path a client takes from "click Order Now" to "payment URL
returned": validates Service + Package loading, fee math, DB inserts, and
the QiCard client invocation boundary.

QiCardClient is mocked at import time (get_settings() → new client) so no
network calls are made; only the fake payment URL is returned. Everything
else hits the real test Postgres provisioned by conftest.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import (
    ServiceCategory,
    Service,
    ServicePackage,
    ServicePackageTier,
    ServiceStatus,
    ServiceOrder,
    ServiceOrderStatus,
)
from app.models.user import User
from app.schemas.service import ServiceOrderCreate
from app.services.catalog_service import CatalogService


@pytest_asyncio.fixture
async def sample_category(db_session: AsyncSession) -> ServiceCategory:
    """Create a service category — required by Service foreign key."""
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
async def active_service_with_package(
    db_session: AsyncSession,
    sample_freelancer_user: User,
    sample_category: ServiceCategory,
) -> tuple[Service, ServicePackage]:
    """A published ACTIVE service with one Basic package at 200,000 IQD."""
    service = Service(
        id=uuid.uuid4(),
        freelancer_id=sample_freelancer_user.id,
        category_id=sample_category.id,
        title="I will build a FastAPI backend for your startup",
        description="Production-grade FastAPI service with Postgres, auth, and tests.",
        slug=f"fastapi-backend-{uuid.uuid4().hex[:6]}",
        status=ServiceStatus.ACTIVE,
        tags=["python", "fastapi", "postgres"],
    )
    db_session.add(service)
    await db_session.flush()

    package = ServicePackage(
        id=uuid.uuid4(),
        service_id=service.id,
        tier=ServicePackageTier.BASIC,
        name="Basic Setup",
        description="Auth + CRUD for one resource, deployed.",
        price=Decimal("200000"),  # 200,000 IQD
        delivery_days=5,
        revisions=2,
    )
    db_session.add(package)
    await db_session.flush()

    # Refresh the service so its .packages relationship is populated for
    # _load_service's selectinload to find.
    await db_session.refresh(service)

    return service, package


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_place_order_creates_pending_order_and_returns_payment_url(
    db_session: AsyncSession,
    sample_client_user: User,
    active_service_with_package: tuple[Service, ServicePackage],
):
    """Happy path: place_order creates PENDING order + increments orders_count."""
    service, package = active_service_with_package
    svc = CatalogService(db_session)

    fake_payment_url = "https://uat.pay.qi.iq/checkout/abc123"
    with patch(
        "app.services.catalog_service.QiCardClient",
        autospec=True,
    ) as MockQi:
        instance = MockQi.return_value
        instance.create_payment = AsyncMock(return_value={"link": fake_payment_url})

        order, payment_url = await svc.place_order(
            sample_client_user,
            ServiceOrderCreate(
                service_id=service.id,
                package_id=package.id,
                requirements="Please deploy to Hetzner; I prefer Python 3.12.",
            ),
        )

    # Payment boundary
    assert payment_url == fake_payment_url
    instance.create_payment.assert_awaited_once()
    call_kwargs = instance.create_payment.await_args.kwargs
    assert call_kwargs["amount_iqd"] == 200000  # whole IQD, no fractional
    assert call_kwargs["order_id"].startswith("gig-order-")  # backward-compat prefix

    # Order record
    assert order.status == ServiceOrderStatus.PENDING
    assert str(order.client_id) == str(sample_client_user.id)
    assert str(order.freelancer_id) == str(service.freelancer_id)
    assert float(order.price_paid) == 200000.0
    assert order.delivery_days == 5
    assert order.revisions_remaining == 2
    assert order.requirements == "Please deploy to Hetzner; I prefer Python 3.12."

    # Service.orders_count was incremented
    result = await db_session.execute(select(Service).where(Service.id == service.id))
    refreshed = result.scalar_one()
    assert refreshed.orders_count == 1


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_place_order_rejects_self_ordering(
    db_session: AsyncSession,
    sample_freelancer_user: User,
    active_service_with_package: tuple[Service, ServicePackage],
):
    """Freelancer cannot order their own service."""
    from app.core.exceptions import BadRequestError

    service, package = active_service_with_package
    svc = CatalogService(db_session)

    with patch("app.services.catalog_service.QiCardClient"):
        with pytest.raises(BadRequestError) as exc:
            await svc.place_order(
                sample_freelancer_user,  # service.freelancer_id == this user
                ServiceOrderCreate(service_id=service.id, package_id=package.id),
            )

    assert "own service" in str(exc.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_place_order_rejects_inactive_service(
    db_session: AsyncSession,
    sample_client_user: User,
    active_service_with_package: tuple[Service, ServicePackage],
):
    """Cannot order a service that's pending review or paused."""
    from app.core.exceptions import NotFoundError

    service, package = active_service_with_package

    # Flip to pending_review and persist
    service.status = ServiceStatus.PENDING_REVIEW
    await db_session.flush()

    svc = CatalogService(db_session)
    with patch("app.services.catalog_service.QiCardClient"):
        with pytest.raises(NotFoundError):
            await svc.place_order(
                sample_client_user,
                ServiceOrderCreate(service_id=service.id, package_id=package.id),
            )
