"""
Kaasb Platform - Buyer Request Service
Business logic for buyer requests (Fiverr-style "Post a Request").
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.buyer_request import (
    BuyerRequest,
    BuyerRequestOffer,
    BuyerRequestOfferStatus,
    BuyerRequestStatus,
)
from app.models.notification import NotificationType
from app.models.service import Service, ServiceCategory
from app.models.user import User, UserRole
from app.schemas.buyer_request import BuyerRequestCreate, BuyerRequestOfferCreate
from app.services.base import BaseService
from app.services.notification_service import notify_background

MAX_ACTIVE_REQUESTS_PER_CLIENT = 10
MAX_OFFERS_PER_REQUEST = 10
REQUEST_EXPIRY_DAYS = 7


class BuyerRequestService(BaseService):
    """Service for buyer request marketplace operations."""

    # ──────────────────────────────────────────
    # Request CRUD
    # ──────────────────────────────────────────

    async def create_request(self, client: User, data: BuyerRequestCreate) -> BuyerRequest:
        if client.primary_role == UserRole.ADMIN:
            raise ForbiddenError("Admins cannot post buyer requests")

        # Enforce per-client active limit
        count_result = await self.db.execute(
            select(func.count(BuyerRequest.id)).where(
                BuyerRequest.client_id == client.id,
                BuyerRequest.status == BuyerRequestStatus.OPEN,
            )
        )
        active_count = count_result.scalar_one()
        if active_count >= MAX_ACTIVE_REQUESTS_PER_CLIENT:
            raise BadRequestError(
                f"You already have {MAX_ACTIVE_REQUESTS_PER_CLIENT} open requests. "
                "Fill or cancel one before posting another."
            )

        # Validate budget ordering
        if data.budget_min > data.budget_max:
            raise BadRequestError("budget_min cannot exceed budget_max")

        # Validate category if provided
        if data.category_id:
            cat = await self.db.get(ServiceCategory, data.category_id)
            if not cat:
                raise NotFoundError("Category")

        req = BuyerRequest(
            client_id=client.id,
            title=data.title,
            description=data.description,
            category_id=data.category_id,
            budget_min=data.budget_min,
            budget_max=data.budget_max,
            delivery_days=data.delivery_days,
            status=BuyerRequestStatus.OPEN,
            expires_at=datetime.now(UTC) + timedelta(days=REQUEST_EXPIRY_DAYS),
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)
        return await self._load_request(req.id)  # type: ignore[return-value]

    async def list_requests(
        self,
        page: int = 1,
        page_size: int = 20,
        category_id: uuid.UUID | None = None,
    ) -> tuple[list[BuyerRequest], int]:
        """Freelancers browse open, non-expired requests."""
        now = datetime.now(UTC)
        q = (
            select(BuyerRequest)
            .where(
                BuyerRequest.status == BuyerRequestStatus.OPEN,
                BuyerRequest.expires_at > now,
            )
            .options(
                selectinload(BuyerRequest.client),
                selectinload(BuyerRequest.category),
                selectinload(BuyerRequest.offers),
            )
        )
        if category_id:
            q = q.where(BuyerRequest.category_id == category_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = q.order_by(BuyerRequest.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(q)
        requests = list(result.scalars().all())
        return requests, total

    async def get_request(self, request_id: uuid.UUID) -> BuyerRequest:
        req = await self._load_request(request_id)
        if not req:
            raise NotFoundError("Buyer request")
        return req

    async def my_requests(self, client: User) -> list[BuyerRequest]:
        result = await self.db.execute(
            select(BuyerRequest)
            .where(BuyerRequest.client_id == client.id)
            .options(
                selectinload(BuyerRequest.category),
                selectinload(BuyerRequest.offers).selectinload(BuyerRequestOffer.freelancer),
                selectinload(BuyerRequest.offers).selectinload(BuyerRequestOffer.service),
            )
            .order_by(BuyerRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def cancel_request(self, request_id: uuid.UUID, client: User) -> BuyerRequest:
        req = await self._load_request(request_id)
        if not req:
            raise NotFoundError("Buyer request")
        if req.client_id != client.id:
            raise ForbiddenError("Access denied")
        if req.status != BuyerRequestStatus.OPEN:
            raise BadRequestError(f"Cannot cancel a request with status '{req.status.value}'")
        req.status = BuyerRequestStatus.CANCELLED
        await self.db.commit()
        return await self._load_request(req.id)  # type: ignore[return-value]

    # ──────────────────────────────────────────
    # Offer lifecycle
    # ──────────────────────────────────────────

    async def send_offer(
        self,
        request_id: uuid.UUID,
        freelancer: User,
        data: BuyerRequestOfferCreate,
    ) -> BuyerRequestOffer:
        req = await self._load_request(request_id)
        if not req:
            raise NotFoundError("Buyer request")
        if req.status != BuyerRequestStatus.OPEN:
            raise BadRequestError("This request is no longer accepting offers")
        if datetime.now(UTC) > req.expires_at:
            raise BadRequestError("This request has expired")
        if freelancer.primary_role not in (UserRole.FREELANCER, UserRole.ADMIN):
            raise ForbiddenError("Only freelancers can send offers")
        if req.client_id == freelancer.id:
            raise BadRequestError("Cannot send an offer on your own request")

        # Max 10 offers per request
        count_result = await self.db.execute(
            select(func.count(BuyerRequestOffer.id)).where(
                BuyerRequestOffer.request_id == request_id,
                BuyerRequestOffer.status != BuyerRequestOfferStatus.REJECTED,
            )
        )
        if count_result.scalar_one() >= MAX_OFFERS_PER_REQUEST:
            raise BadRequestError("This request has reached the maximum number of offers")

        # Each freelancer can only send one offer per request
        existing = await self.db.execute(
            select(BuyerRequestOffer).where(
                BuyerRequestOffer.request_id == request_id,
                BuyerRequestOffer.freelancer_id == freelancer.id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("You have already sent an offer for this request")

        service_ref_id = getattr(data, "service_id", None) or getattr(data, "gig_id", None)
        if service_ref_id:
            svc = await self.db.get(Service, service_ref_id)
            if not svc or str(svc.freelancer_id) != str(freelancer.id):
                raise BadRequestError("Service not found or does not belong to you")

        offer = BuyerRequestOffer(
            request_id=request_id,
            freelancer_id=freelancer.id,
            service_id=service_ref_id,
            price=data.price,
            delivery_days=data.delivery_days,
            message=data.message,
            status=BuyerRequestOfferStatus.PENDING,
        )
        self.db.add(offer)
        await self.db.commit()
        await self.db.refresh(offer)

        # Notify the client
        asyncio.create_task(notify_background(
            user_id=req.client_id,
            type=NotificationType.BUYER_REQUEST_OFFER_RECEIVED,
            title="عرض جديد على طلبك",
            message=f'أرسل {freelancer.first_name} عرضاً على طلبك "{req.title[:80]}"',
            link_type="buyer_request",
            link_id=str(request_id),
            actor_id=freelancer.id,
        ))

        return await self._load_offer(offer.id)  # type: ignore[return-value]

    async def accept_offer(
        self,
        request_id: uuid.UUID,
        offer_id: uuid.UUID,
        client: User,
    ) -> BuyerRequestOffer:
        """Accept an offer. Marks the request as filled, rejects all other offers."""
        req = await self._load_request(request_id)
        if not req:
            raise NotFoundError("Buyer request")
        if req.client_id != client.id:
            raise ForbiddenError("Access denied")
        if req.status != BuyerRequestStatus.OPEN:
            raise BadRequestError("This request is no longer open")

        offer = await self.db.get(BuyerRequestOffer, offer_id)
        if not offer or offer.request_id != request_id:
            raise NotFoundError("Offer")
        if offer.status != BuyerRequestOfferStatus.PENDING:
            raise BadRequestError(f"Offer status is '{offer.status.value}', cannot accept")

        offer.status = BuyerRequestOfferStatus.ACCEPTED
        req.status = BuyerRequestStatus.FILLED

        # Reject remaining pending offers
        await self.db.execute(
            select(BuyerRequestOffer)
            .where(
                BuyerRequestOffer.request_id == request_id,
                BuyerRequestOffer.id != offer_id,
                BuyerRequestOffer.status == BuyerRequestOfferStatus.PENDING,
            )
        )
        # Use SQL update for bulk rejection
        from sqlalchemy import update as sql_update
        await self.db.execute(
            sql_update(BuyerRequestOffer)
            .where(
                BuyerRequestOffer.request_id == request_id,
                BuyerRequestOffer.id != offer_id,
                BuyerRequestOffer.status == BuyerRequestOfferStatus.PENDING,
            )
            .values(status=BuyerRequestOfferStatus.REJECTED)
        )

        await self.db.commit()

        # Notify the freelancer whose offer was accepted
        asyncio.create_task(notify_background(
            user_id=offer.freelancer_id,
            type=NotificationType.BUYER_REQUEST_OFFER_ACCEPTED,
            title="تم قبول عرضك",
            message=f'قبل العميل عرضك على طلب "{req.title[:80]}"',
            link_type="buyer_request",
            link_id=str(request_id),
            actor_id=client.id,
        ))

        return await self._load_offer(offer.id)  # type: ignore[return-value]

    async def reject_offer(
        self,
        request_id: uuid.UUID,
        offer_id: uuid.UUID,
        client: User,
    ) -> BuyerRequestOffer:
        req = await self.db.get(BuyerRequest, request_id)
        if not req:
            raise NotFoundError("Buyer request")
        if req.client_id != client.id:
            raise ForbiddenError("Access denied")

        offer = await self.db.get(BuyerRequestOffer, offer_id)
        if not offer or offer.request_id != request_id:
            raise NotFoundError("Offer")
        if offer.status != BuyerRequestOfferStatus.PENDING:
            raise BadRequestError(f"Offer status is '{offer.status.value}', cannot reject")

        offer.status = BuyerRequestOfferStatus.REJECTED
        await self.db.commit()

        asyncio.create_task(notify_background(
            user_id=offer.freelancer_id,
            type=NotificationType.BUYER_REQUEST_OFFER_REJECTED,
            title="تم رفض عرضك",
            message=f'رفض العميل عرضك على طلب "{req.title[:80]}"',
            link_type="buyer_request",
            link_id=str(request_id),
            actor_id=client.id,
        ))

        return await self._load_offer(offer.id)  # type: ignore[return-value]

    async def list_offers_for_request(
        self,
        request_id: uuid.UUID,
        client: User,
    ) -> list[BuyerRequestOffer]:
        """Client views all offers on their request."""
        req = await self.db.get(BuyerRequest, request_id)
        if not req:
            raise NotFoundError("Buyer request")
        if req.client_id != client.id:
            raise ForbiddenError("Access denied")

        result = await self.db.execute(
            select(BuyerRequestOffer)
            .where(BuyerRequestOffer.request_id == request_id)
            .options(
                selectinload(BuyerRequestOffer.freelancer),
                selectinload(BuyerRequestOffer.service),
            )
            .order_by(BuyerRequestOffer.created_at.asc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Background task: expire old requests
    # ──────────────────────────────────────────

    async def expire_old_requests(self) -> int:
        """Set status=expired on OPEN requests past their expires_at. Returns count."""
        from sqlalchemy import update as sql_update
        result = await self.db.execute(
            sql_update(BuyerRequest)
            .where(
                BuyerRequest.status == BuyerRequestStatus.OPEN,
                BuyerRequest.expires_at < datetime.now(UTC),
            )
            .values(status=BuyerRequestStatus.EXPIRED)
        )
        await self.db.commit()
        return result.rowcount

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    async def _load_request(self, request_id: uuid.UUID) -> BuyerRequest | None:
        result = await self.db.execute(
            select(BuyerRequest)
            .where(BuyerRequest.id == request_id)
            .options(
                selectinload(BuyerRequest.client),
                selectinload(BuyerRequest.category),
                selectinload(BuyerRequest.offers).selectinload(BuyerRequestOffer.freelancer),
                selectinload(BuyerRequest.offers).selectinload(BuyerRequestOffer.service),
            )
        )
        return result.scalar_one_or_none()

    async def _load_offer(self, offer_id: uuid.UUID) -> BuyerRequestOffer | None:
        result = await self.db.execute(
            select(BuyerRequestOffer)
            .where(BuyerRequestOffer.id == offer_id)
            .options(
                selectinload(BuyerRequestOffer.freelancer),
                selectinload(BuyerRequestOffer.service),
            )
        )
        return result.scalar_one_or_none()
