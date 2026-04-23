"""Integration test — service-order requirements submission (F3).

Tests catalog_service.submit_requirements end-to-end: client answers the
service's requirement questions, order transitions PENDING_REQUIREMENTS
→ IN_PROGRESS, due_date is recalculated from now().
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ForbiddenError
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
        name_en="Writing",
        name_ar="كتابة",
        slug=f"writing-{uuid.uuid4().hex[:6]}",
        icon="pen",
        is_active=True,
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


@pytest_asyncio.fixture
async def pending_requirements_order(
    db_session: AsyncSession,
    sample_client_user: User,
    sample_freelancer_user: User,
    sample_category: ServiceCategory,
) -> ServiceOrder:
    """Order in PENDING_REQUIREMENTS state — waiting for client to answer."""
    service = Service(
        id=uuid.uuid4(),
        freelancer_id=sample_freelancer_user.id,
        category_id=sample_category.id,
        title="I will write SEO-optimized blog posts for you",
        description="Research-driven blog content tailored to your niche and audience.",
        slug=f"blog-writing-{uuid.uuid4().hex[:6]}",
        status=ServiceStatus.ACTIVE,
        requirement_questions=[
            {"question": "What is the topic?", "type": "text", "required": True},
            {"question": "Target word count?", "type": "text", "required": True},
        ],
    )
    package = ServicePackage(
        id=uuid.uuid4(),
        service_id=service.id,
        tier=ServicePackageTier.BASIC,
        name="500-word Post",
        description="One SEO-optimized blog post up to 500 words.",
        price=Decimal("30000"),
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
        status=ServiceOrderStatus.PENDING_REQUIREMENTS,
        price_paid=30000.0,
        delivery_days=3,
        revisions_remaining=1,
    )
    db_session.add(order)
    await db_session.flush()
    return order


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_client_submits_requirements_starts_order(
    db_session: AsyncSession,
    sample_client_user: User,
    pending_requirements_order: ServiceOrder,
):
    """PENDING_REQUIREMENTS → IN_PROGRESS + due_date reset from now."""
    svc = CatalogService(db_session)
    answers = [
        {"question": "What is the topic?", "answer": "Iraqi coffee culture"},
        {"question": "Target word count?", "answer": "500"},
    ]

    before_submit = datetime.now(UTC)
    with patch("app.services.catalog_service.asyncio.create_task"):
        updated = await svc.submit_requirements(
            pending_requirements_order.id, sample_client_user, answers
        )

    assert updated.status == ServiceOrderStatus.IN_PROGRESS
    assert updated.requirement_answers == answers
    assert updated.requirements_submitted_at is not None
    assert updated.requirements_submitted_at >= before_submit

    # due_date rescheduled from now + delivery_days (3 days)
    assert updated.due_date is not None
    delta = updated.due_date - datetime.now(UTC)
    assert 2.9 * 86400 <= delta.total_seconds() <= 3.1 * 86400


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_freelancer_cannot_submit_requirements(
    db_session: AsyncSession,
    sample_freelancer_user: User,
    pending_requirements_order: ServiceOrder,
):
    """Only the order's client can submit requirements."""
    svc = CatalogService(db_session)
    with patch("app.services.catalog_service.asyncio.create_task"):
        with pytest.raises(ForbiddenError):
            await svc.submit_requirements(
                pending_requirements_order.id,
                sample_freelancer_user,
                [{"question": "q", "answer": "a"}],
            )


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_cannot_resubmit_once_in_progress(
    db_session: AsyncSession,
    sample_client_user: User,
    pending_requirements_order: ServiceOrder,
):
    """Once the order has moved to IN_PROGRESS, requirements can't be resubmitted."""
    pending_requirements_order.status = ServiceOrderStatus.IN_PROGRESS
    await db_session.flush()

    svc = CatalogService(db_session)
    with patch("app.services.catalog_service.asyncio.create_task"):
        with pytest.raises(BadRequestError) as exc:
            await svc.submit_requirements(
                pending_requirements_order.id,
                sample_client_user,
                [{"question": "q", "answer": "a"}],
            )
    assert "requirements" in str(exc.value).lower() or "in_progress" in str(exc.value).lower()
