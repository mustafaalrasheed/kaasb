"""Integration test — Buyer Request → Offer → Accept flow (F1).

Exercises BuyerRequestService end-to-end:
- Client posts a request (create_request)
- Freelancers send offers (send_offer)
- Client accepts one offer; request flips to FILLED, rival offers rejected
- Validation rejections (self-offer, duplicate offer, closed request)

Background notification tasks are suppressed so tests don't depend on
async task completion timing.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError
from app.models.buyer_request import (
    BuyerRequest,
    BuyerRequestOffer,
    BuyerRequestOfferStatus,
    BuyerRequestStatus,
)
from app.models.user import User, UserRole, UserStatus
from app.schemas.buyer_request import BuyerRequestCreate, BuyerRequestOfferCreate
from app.services.buyer_request_service import BuyerRequestService


@pytest_asyncio.fixture
async def second_freelancer(db_session: AsyncSession) -> User:
    """A second freelancer so we can test rival offers being auto-rejected."""
    from app.core.security import hash_password

    user = User(
        id=uuid.uuid4(),
        email="freelancer2@test.com",
        username="testfreelancer2",
        hashed_password=hash_password("TestPass1!"),
        first_name="Second",
        last_name="Freelancer",
        primary_role=UserRole.FREELANCER,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
        skills=["Design", "Figma"],
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def open_buyer_request(
    db_session: AsyncSession, sample_client_user: User
) -> BuyerRequest:
    """A fresh OPEN buyer request that freelancers can bid on."""
    req = BuyerRequest(
        id=uuid.uuid4(),
        client_id=sample_client_user.id,
        title="Need a logo for my small Baghdad bakery",
        description="Looking for a modern but warm logo design, gold and brown tones, square SVG.",
        budget_min=Decimal("50000"),
        budget_max=Decimal("150000"),
        delivery_days=7,
        status=BuyerRequestStatus.OPEN,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(req)
    await db_session.flush()
    return req


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_client_creates_buyer_request(
    db_session: AsyncSession, sample_client_user: User
):
    """Client creates a buyer request → stored with status OPEN + expires_at set."""
    svc = BuyerRequestService(db_session)

    # notify_background runs in asyncio.create_task — suppress it so the test
    # doesn't depend on background task scheduling.
    with patch("app.services.buyer_request_service.asyncio.create_task"):
        req = await svc.create_request(
            sample_client_user,
            BuyerRequestCreate(
                title="Need a website for my restaurant",
                description="Simple 3-page site: menu, contact, gallery. Arabic + English.",
                budget_min=200000,
                budget_max=400000,
                delivery_days=14,
            ),
        )

    assert req.status == BuyerRequestStatus.OPEN
    assert str(req.client_id) == str(sample_client_user.id)
    assert req.expires_at is not None
    assert req.expires_at > datetime.now(UTC)


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_freelancer_sends_offer_on_open_request(
    db_session: AsyncSession,
    sample_freelancer_user: User,
    open_buyer_request: BuyerRequest,
):
    """Freelancer sends an offer → stored as PENDING linked to the request."""
    svc = BuyerRequestService(db_session)

    with patch("app.services.buyer_request_service.asyncio.create_task"):
        offer = await svc.send_offer(
            open_buyer_request.id,
            sample_freelancer_user,
            BuyerRequestOfferCreate(
                price=100000,
                delivery_days=5,
                message="I specialize in Iraqi food-service branding and can deliver a warm, gold-accented logo with 2 revisions included.",
            ),
        )

    assert offer.status == BuyerRequestOfferStatus.PENDING
    assert str(offer.request_id) == str(open_buyer_request.id)
    assert str(offer.freelancer_id) == str(sample_freelancer_user.id)
    assert float(offer.price) == 100000.0


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_client_cannot_offer_on_own_request(
    db_session: AsyncSession,
    sample_client_user: User,
    open_buyer_request: BuyerRequest,
):
    """The request owner cannot send an offer on their own request — but only
    if they're a FREELANCER role (client role is already rejected earlier).
    Use the freelancer fixture and make them the request owner to trigger the
    specific self-offer check."""
    # Flip the request to be owned by the freelancer so the role check passes
    # and the self-offer check trips.
    from app.core.security import hash_password

    freelancer_as_client = User(
        id=uuid.uuid4(),
        email="dual-role@test.com",
        username="dualrole",
        hashed_password=hash_password("TestPass1!"),
        first_name="Dual",
        last_name="Role",
        primary_role=UserRole.FREELANCER,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add(freelancer_as_client)
    await db_session.flush()

    open_buyer_request.client_id = freelancer_as_client.id
    await db_session.flush()

    svc = BuyerRequestService(db_session)
    with patch("app.services.buyer_request_service.asyncio.create_task"):
        with pytest.raises(BadRequestError) as exc:
            await svc.send_offer(
                open_buyer_request.id,
                freelancer_as_client,
                BuyerRequestOfferCreate(
                    price=100000,
                    delivery_days=5,
                    message="Trying to offer on my own request to verify guard.",
                ),
            )
    assert "own request" in str(exc.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_freelancer_cannot_duplicate_offers(
    db_session: AsyncSession,
    sample_freelancer_user: User,
    open_buyer_request: BuyerRequest,
):
    """Same freelancer sending a second offer on the same request → ConflictError."""
    svc = BuyerRequestService(db_session)
    offer_data = BuyerRequestOfferCreate(
        price=100000,
        delivery_days=5,
        message="First offer with enough characters to satisfy the minimum length.",
    )

    with patch("app.services.buyer_request_service.asyncio.create_task"):
        await svc.send_offer(open_buyer_request.id, sample_freelancer_user, offer_data)

        # Second offer from same freelancer on same request should fail
        with pytest.raises(ConflictError) as exc:
            await svc.send_offer(
                open_buyer_request.id,
                sample_freelancer_user,
                BuyerRequestOfferCreate(
                    price=90000,
                    delivery_days=4,
                    message="Second offer trying to undercut the first one.",
                ),
            )
    assert "already sent" in str(exc.value).lower()


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="session")
async def test_accept_offer_fills_request_and_rejects_rivals(
    db_session: AsyncSession,
    sample_client_user: User,
    sample_freelancer_user: User,
    second_freelancer: User,
    open_buyer_request: BuyerRequest,
):
    """Client accepts one offer → request FILLED + rival offers REJECTED."""
    svc = BuyerRequestService(db_session)

    with patch("app.services.buyer_request_service.asyncio.create_task"):
        accepted = await svc.send_offer(
            open_buyer_request.id,
            sample_freelancer_user,
            BuyerRequestOfferCreate(
                price=100000,
                delivery_days=5,
                message="Strong offer from freelancer one, 5-day delivery and 2 revisions included.",
            ),
        )
        rival = await svc.send_offer(
            open_buyer_request.id,
            second_freelancer,
            BuyerRequestOfferCreate(
                price=85000,
                delivery_days=7,
                message="Cheaper but slower offer from freelancer two — 7 day delivery with unlimited revisions.",
            ),
        )

        result = await svc.accept_offer(
            open_buyer_request.id, accepted.id, sample_client_user
        )

    assert result.status == BuyerRequestOfferStatus.ACCEPTED
    assert str(result.id) == str(accepted.id)

    # Request is now FILLED
    await db_session.refresh(open_buyer_request)
    assert open_buyer_request.status == BuyerRequestStatus.FILLED

    # Rival offer got auto-rejected
    await db_session.refresh(rival)
    assert rival.status == BuyerRequestOfferStatus.REJECTED
