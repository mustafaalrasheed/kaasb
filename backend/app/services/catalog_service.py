"""
Kaasb Platform - Catalog Service
Business logic for the Fiverr-style service marketplace (خدمة / khidma).

Named ``CatalogService`` (not ``ServiceService``) because the backend folder
``app/services/`` already holds business-logic classes. ``Catalog`` keeps the
layer-vs-domain boundary readable.
"""

import asyncio
import hashlib
import hmac as _hmac
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ExternalServiceError, ForbiddenError, NotFoundError
from app.models.message import Conversation, ConversationType
from app.models.notification import NotificationType
from app.models.payment import (
    Escrow,
    EscrowStatus,
    PaymentProvider,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.models.service import (
    Service,
    ServiceCategory,
    ServiceOrder,
    ServiceOrderDelivery,
    ServiceOrderStatus,
    ServicePackage,
    ServiceStatus,
)
from app.models.user import User, UserRole, UserStatus
from app.schemas.service import (
    ServiceCreate,
    ServiceOrderCreate,
    ServiceSearchParams,
    ServiceUpdate,
)
from app.services.base import BaseService
from app.services.notification_service import notify_background
from app.services.qi_card_client import QiCardClient, QiCardError
from app.utils.files import MAX_SERVICE_IMAGES, delete_service_image

logger = logging.getLogger(__name__)


def _slugify(text: str, suffix: str = "") -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug[:100]
    if suffix:
        slug = f"{slug}-{suffix}"
    return slug


class CatalogService(BaseService):
    """Service-layer class for the service-catalog marketplace."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    # ──────────────────────────────────────────
    # Categories
    # ──────────────────────────────────────────

    async def list_categories(self) -> list[ServiceCategory]:
        result = await self.db.execute(
            select(ServiceCategory)
            .where(ServiceCategory.is_active == True)  # noqa: E712
            .options(selectinload(ServiceCategory.subcategories))
            .order_by(ServiceCategory.sort_order)
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Service CRUD
    # ──────────────────────────────────────────

    async def create_service(self, freelancer: User, data: ServiceCreate) -> Service:
        if freelancer.primary_role not in (UserRole.FREELANCER, UserRole.ADMIN):
            raise ForbiddenError("Only freelancers can create services")

        cat = await self.db.get(ServiceCategory, data.category_id)
        if not cat:
            raise NotFoundError("Category")

        base_slug = _slugify(data.title)
        slug = await self._unique_slug(base_slug)

        req_questions = [q.model_dump() for q in (data.requirement_questions or [])]

        service = Service(
            freelancer_id=freelancer.id,
            title=data.title,
            slug=slug,
            description=data.description,
            category_id=data.category_id,
            subcategory_id=data.subcategory_id,
            tags=data.tags,
            requirement_questions=req_questions if req_questions else None,
            status=ServiceStatus.PENDING_REVIEW,
        )
        self.db.add(service)
        await self.db.flush()  # get service.id

        for pkg_data in data.packages:
            pkg = ServicePackage(
                service_id=service.id,
                tier=pkg_data.tier,
                name=pkg_data.name,
                description=pkg_data.description,
                price=pkg_data.price,
                delivery_days=pkg_data.delivery_days,
                revisions=pkg_data.revisions,
                features=pkg_data.features,
            )
            self.db.add(pkg)

        await self.db.commit()
        await self.db.refresh(service)

        # Collect admin IDs + service snapshot BEFORE _load_service so notify tasks
        # are scheduled after the load completes (avoids concurrent AsyncSession use).
        admin_result = await self.db.execute(
            select(User).where(
                User.is_superuser == True,  # noqa: E712
                User.status == UserStatus.ACTIVE,
            )
        )
        admin_ids = [admin.id for admin in admin_result.scalars().all()]
        service_title = service.title
        service_id_str = str(service.id)
        freelancer_username = freelancer.username

        loaded_service = await self._load_service(service.id)

        for admin_id in admin_ids:
            asyncio.create_task(notify_background(
                user_id=admin_id,
                type=NotificationType.SERVICE_SUBMITTED,
                title_ar="خدمة جديدة بانتظار المراجعة",
                title_en="New service pending review",
                message_ar=f'"{service_title}" من {freelancer_username} بانتظار الموافقة.',
                message_en=f'"{service_title}" by {freelancer_username} is awaiting approval.',
                link_type="service",
                link_id=service_id_str,
            ))

        return loaded_service  # type: ignore[return-value]

    async def get_service_by_slug(self, slug: str) -> Service:
        service = await self._load_service_by_slug(slug)
        if not service:
            raise NotFoundError("Service")
        if service.status != ServiceStatus.ACTIVE:
            raise NotFoundError("Service")
        # Increment impressions via a bulk UPDATE. synchronize_session=False is
        # critical — without it, the in-memory instance is expired and FastAPI's
        # response serializer tries to lazily refresh columns outside the async ctx.
        await self.db.execute(
            update(Service)
            .where(Service.id == service.id)
            .values(impressions=Service.impressions + 1)
            .execution_options(synchronize_session=False)
        )
        await self.db.commit()
        return service

    async def get_service_by_id_for_owner(self, service_id: uuid.UUID, user: User) -> Service:
        """Get any service (any status) for the owner or admin."""
        service = await self._load_service(service_id)
        if not service:
            raise NotFoundError("Service")
        if service.freelancer_id != user.id and user.primary_role != UserRole.ADMIN:
            raise ForbiddenError("Access denied")
        return service

    async def update_service(self, service_id: uuid.UUID, user: User, data: ServiceUpdate) -> Service:
        service = await self.get_service_by_id_for_owner(service_id, user)

        if data.title is not None:
            service.title = data.title
            service.slug = await self._unique_slug(_slugify(data.title), exclude_id=service.id)
        if data.description is not None:
            service.description = data.description
        if data.category_id is not None:
            service.category_id = data.category_id
        if data.subcategory_id is not None:
            service.subcategory_id = data.subcategory_id
        if data.tags is not None:
            service.tags = data.tags
        if data.requirement_questions is not None:
            service.requirement_questions = [q.model_dump() for q in data.requirement_questions] or None

        if data.packages is not None:
            for old_pkg in service.packages:
                await self.db.delete(old_pkg)
            await self.db.flush()
            for pkg_data in data.packages:
                pkg = ServicePackage(
                    service_id=service.id,
                    tier=pkg_data.tier,
                    name=pkg_data.name,
                    description=pkg_data.description,
                    price=pkg_data.price,
                    delivery_days=pkg_data.delivery_days,
                    revisions=pkg_data.revisions,
                    features=pkg_data.features,
                )
                self.db.add(pkg)

        if service.status in (ServiceStatus.ACTIVE, ServiceStatus.NEEDS_REVISION):
            service.status = ServiceStatus.PENDING_REVIEW
            service.revision_note = None

        await self.db.commit()
        return await self._load_service(service.id)  # type: ignore[return-value]

    async def delete_service(self, service_id: uuid.UUID, user: User) -> None:
        service = await self.get_service_by_id_for_owner(service_id, user)
        if service.orders_count > 0:
            raise BadRequestError("Cannot delete a service that has orders — archive it instead")
        await self.db.delete(service)
        await self.db.commit()

    async def pause_service(self, service_id: uuid.UUID, user: User) -> Service:
        service = await self.get_service_by_id_for_owner(service_id, user)
        if service.status not in (ServiceStatus.ACTIVE,):
            raise BadRequestError("Only active services can be paused")
        service.status = ServiceStatus.PAUSED
        await self.db.commit()
        return await self._load_service(service.id)  # type: ignore[return-value]

    async def resume_service(self, service_id: uuid.UUID, user: User) -> Service:
        service = await self.get_service_by_id_for_owner(service_id, user)
        if service.status != ServiceStatus.PAUSED:
            raise BadRequestError("Only paused services can be resumed")
        service.status = ServiceStatus.ACTIVE
        await self.db.commit()
        return await self._load_service(service.id)  # type: ignore[return-value]

    # ──────────────────────────────────────────
    # Search / Listing
    # ──────────────────────────────────────────

    async def search_services(
        self, params: ServiceSearchParams
    ) -> tuple[list[Service], int]:
        """Returns (services, total_count) for the given search params."""
        q = (
            select(Service)
            .where(Service.status == ServiceStatus.ACTIVE)
            .options(
                selectinload(Service.freelancer),
                selectinload(Service.packages),
                selectinload(Service.category),
            )
        )

        if params.q:
            term = f"%{params.q}%"
            q = q.where(
                or_(
                    Service.title.ilike(term),
                    Service.description.ilike(term),
                )
            )
        if params.category_id:
            q = q.where(Service.category_id == params.category_id)
        if params.subcategory_id:
            q = q.where(Service.subcategory_id == params.subcategory_id)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        sort_map = {
            "relevance": Service.rank_score.desc(),
            "newest": Service.created_at.desc(),
            "rating": Service.avg_rating.desc(),
            "orders": Service.orders_count.desc(),
        }
        if not params.q and params.sort_by not in ("newest", "rating", "orders"):
            order_col = Service.rank_score.desc()
        else:
            order_col = sort_map.get(params.sort_by, Service.rank_score.desc())
        q = q.order_by(order_col)

        offset = (params.page - 1) * params.page_size
        q = q.offset(offset).limit(params.page_size)

        result = await self.db.execute(q)
        services = list(result.scalars().all())
        return services, total

    async def list_my_services(self, freelancer: User) -> list[Service]:
        result = await self.db.execute(
            select(Service)
            .where(Service.freelancer_id == freelancer.id)
            .options(selectinload(Service.packages), selectinload(Service.category))
            .order_by(Service.created_at.desc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Admin Review
    # ──────────────────────────────────────────

    async def approve_service(self, service_id: uuid.UUID, admin: User) -> Service:
        service = await self._load_service(service_id)
        if not service:
            raise NotFoundError("Service")
        if service.status not in (ServiceStatus.PENDING_REVIEW, ServiceStatus.NEEDS_REVISION):
            raise BadRequestError(f"Cannot approve a service with status '{service.status.value}'.")
        freelancer_id = service.freelancer_id
        service_title = service.title
        service_id_str = str(service.id)

        service.status = ServiceStatus.ACTIVE
        service.rejection_reason = None
        service.reviewed_by_id = admin.id
        service.reviewed_at = datetime.now(UTC)
        await self.db.commit()

        updated_service = await self._load_service(service_id)

        asyncio.create_task(notify_background(
            user_id=freelancer_id,
            type=NotificationType.SERVICE_APPROVED,
            title_ar="تمت الموافقة على خدمتك",
            title_en="Your service was approved",
            message_ar=f'خدمتك "{service_title}" منشورة الآن وظاهرة للعملاء.',
            message_en=f'Your service "{service_title}" is now live and visible to clients.',
            link_type="service",
            link_id=service_id_str,
        ))
        return updated_service  # type: ignore[return-value]

    async def request_service_revision(self, service_id: uuid.UUID, note: str, admin: User) -> Service:
        service = await self._load_service(service_id)
        if not service:
            raise NotFoundError("Service")
        if service.status not in (
            ServiceStatus.PENDING_REVIEW,
            ServiceStatus.NEEDS_REVISION,
            ServiceStatus.ACTIVE,
        ):
            raise BadRequestError(
                f"Cannot request revision on a service with status '{service.status.value}'."
            )
        freelancer_id = service.freelancer_id
        service_title = service.title
        service_id_str = str(service.id)

        service.status = ServiceStatus.NEEDS_REVISION
        service.revision_note = note
        service.reviewed_by_id = admin.id
        service.reviewed_at = datetime.now(UTC)
        await self.db.commit()

        updated_service = await self._load_service(service_id)

        asyncio.create_task(notify_background(
            user_id=freelancer_id,
            type=NotificationType.SERVICE_NEEDS_REVISION,
            title_ar="خدمتك تحتاج تعديلات قبل النشر",
            title_en="Your service needs edits before it can go live",
            message_ar=f'خدمتك "{service_title}" تحتاج إلى تعديلات: {note}',
            message_en=f'Your service "{service_title}" needs changes: {note}',
            link_type="service",
            link_id=service_id_str,
        ))
        return updated_service  # type: ignore[return-value]

    async def reject_service(self, service_id: uuid.UUID, reason: str, admin: User) -> Service:
        service = await self._load_service(service_id)
        if not service:
            raise NotFoundError("Service")
        if service.status == ServiceStatus.REJECTED:
            return service
        if service.status not in (
            ServiceStatus.PENDING_REVIEW,
            ServiceStatus.NEEDS_REVISION,
            ServiceStatus.ACTIVE,
        ):
            raise BadRequestError(f"Cannot reject a service with status '{service.status.value}'.")
        freelancer_id = service.freelancer_id
        service_title = service.title
        service_id_str = str(service.id)

        service.status = ServiceStatus.REJECTED
        service.rejection_reason = reason
        service.revision_note = None
        service.reviewed_by_id = admin.id
        service.reviewed_at = datetime.now(UTC)
        await self.db.commit()

        updated_service = await self._load_service(service_id)

        asyncio.create_task(notify_background(
            user_id=freelancer_id,
            type=NotificationType.SERVICE_REJECTED,
            title_ar="تم رفض خدمتك",
            title_en="Your service was rejected",
            message_ar=f'خدمتك "{service_title}" مرفوضة. السبب: {reason}',
            message_en=f'Your service "{service_title}" was rejected. Reason: {reason}',
            link_type="service",
            link_id=service_id_str,
        ))
        return updated_service  # type: ignore[return-value]

    async def list_pending_services(self) -> list[Service]:
        result = await self.db.execute(
            select(Service)
            .where(Service.status.in_([ServiceStatus.PENDING_REVIEW, ServiceStatus.NEEDS_REVISION]))
            .options(
                selectinload(Service.freelancer),
                selectinload(Service.packages),
                selectinload(Service.category),
                selectinload(Service.subcategory),
            )
            .order_by(Service.created_at.asc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Images
    # ──────────────────────────────────────────

    async def add_image(self, service_id: uuid.UUID, user: User, image_url: str) -> Service:
        service = await self.get_service_by_id_for_owner(service_id, user)
        current = list(service.images or [])
        if len(current) >= MAX_SERVICE_IMAGES:
            raise BadRequestError(f"Maximum {MAX_SERVICE_IMAGES} images allowed per service")
        current.append(image_url)
        service.images = current
        flag_modified(service, "images")
        if not service.thumbnail_url:
            service.thumbnail_url = image_url
        await self.db.commit()
        return await self._load_service(service.id)  # type: ignore[return-value]

    async def remove_image(self, service_id: uuid.UUID, user: User, index: int) -> Service:
        service = await self.get_service_by_id_for_owner(service_id, user)
        current = list(service.images or [])
        if index < 0 or index >= len(current):
            raise BadRequestError("Image index out of range")
        removed_url = current.pop(index)
        service.images = current
        flag_modified(service, "images")
        if service.thumbnail_url == removed_url:
            service.thumbnail_url = current[0] if current else None
        await self.db.commit()
        delete_service_image(removed_url)
        return await self._load_service(service.id)  # type: ignore[return-value]

    # ──────────────────────────────────────────
    # Orders
    # ──────────────────────────────────────────

    async def place_order(self, client: User, data: ServiceOrderCreate) -> tuple[ServiceOrder, str | None]:
        """
        Create a service order and initiate Qi Card payment.

        Returns (order, payment_url). If Qi Card is not configured (sandbox/dev),
        payment_url is the mock URL. Escrow stays PENDING until payment confirmed.
        """
        if client.primary_role == UserRole.ADMIN:
            raise ForbiddenError("Admins cannot place orders")

        service = await self._load_service(data.service_id)
        if not service or service.status != ServiceStatus.ACTIVE:
            raise NotFoundError("Service")

        if str(service.freelancer_id) == str(client.id):
            raise BadRequestError("Cannot order your own service")

        pkg = next((p for p in service.packages if str(p.id) == str(data.package_id)), None)
        if not pkg:
            raise NotFoundError("Package")

        settings = get_settings()
        fee_rate = Decimal(str(settings.PLATFORM_FEE_PERCENT)) / Decimal("100")
        price_d = Decimal(str(float(pkg.price)))
        platform_fee_d = (price_d * fee_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        freelancer_amount_d = (price_d - platform_fee_d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        due = datetime.now(UTC) + timedelta(days=pkg.delivery_days)

        # F3: if service has requirement questions, start in PENDING_REQUIREMENTS
        # (transitions to IN_PROGRESS after client submits answers in payment_service)
        has_requirements = bool(service.requirement_questions)

        order = ServiceOrder(
            service_id=service.id,
            package_id=pkg.id,
            client_id=client.id,
            freelancer_id=service.freelancer_id,
            status=ServiceOrderStatus.PENDING,  # always PENDING until payment confirmed
            requirements=data.requirements,
            price_paid=float(pkg.price),
            delivery_days=pkg.delivery_days,
            revisions_remaining=pkg.revisions,
            due_date=due,
        )
        _ = has_requirements  # payment_service reads service.requirement_questions after confirmation
        self.db.add(order)

        # Increment order count on service — synchronize_session=False to avoid
        # expiring the in-memory instance (same identity-map row).
        await self.db.execute(
            update(Service)
            .where(Service.id == service.id)
            .values(orders_count=Service.orders_count + 1)
            .execution_options(synchronize_session=False)
        )

        await self.db.flush()

        # Order ref keeps the ``gig-order-`` prefix for backward compatibility with
        # existing Qi Card records in production — PaymentService parses this prefix
        # when confirming callbacks, so changing it would orphan in-flight payments.
        order_ref = f"gig-order-{order.id}"
        sig = _hmac.new(
            settings.SECRET_KEY.encode(),
            order_ref.encode(),
            hashlib.sha256,
        ).hexdigest()
        base = f"https://{settings.DOMAIN}"
        payment_url: str | None = None

        # Round to the nearest whole IQD; plain int() truncates toward zero and
        # systematically underpays by up to 0.99 IQD per order.
        amount_iqd_int = int(price_d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        try:
            qi_card = QiCardClient()
            qi_result = await qi_card.create_payment(
                amount_iqd=amount_iqd_int,
                order_id=order_ref,
                success_url=f"{base}/api/v1/payments/qi-card/success?sig={sig}",
                failure_url=f"{base}/api/v1/payments/qi-card/failure?sig={sig}",
                cancel_url=f"{base}/api/v1/payments/qi-card/cancel?sig={sig}",
            )
            payment_url = qi_result.get("link")
        except QiCardError as e:
            logger.error("Qi Card error during service order %s: %s", order.id, e)
            await self.db.rollback()
            raise ExternalServiceError("Payment gateway error. Please try again later.") from e

        txn = Transaction(
            transaction_type=TransactionType.ESCROW_FUND,
            status=TransactionStatus.PENDING,
            amount=float(price_d),
            currency=settings.QI_CARD_CURRENCY,
            platform_fee=float(platform_fee_d),
            net_amount=float(freelancer_amount_d),
            payer_id=client.id,
            payee_id=service.freelancer_id,
            provider=PaymentProvider.QI_CARD,
            external_transaction_id=order_ref,
            description=f"Service order: {service.title[:100]}",
        )
        self.db.add(txn)
        await self.db.flush()

        escrow = Escrow(
            amount=float(price_d),
            platform_fee=float(platform_fee_d),
            freelancer_amount=float(freelancer_amount_d),
            currency=settings.QI_CARD_CURRENCY,
            status=EscrowStatus.PENDING,
            service_order_id=order.id,
            client_id=client.id,
            freelancer_id=service.freelancer_id,
            funding_transaction_id=txn.id,
        )
        self.db.add(escrow)

        await self.db.commit()
        await self.db.refresh(order)
        return order, payment_url

    async def get_my_orders_as_client(self, client: User) -> list[ServiceOrder]:
        result = await self.db.execute(
            select(ServiceOrder)
            .where(ServiceOrder.client_id == client.id)
            .options(selectinload(ServiceOrder.service))
            .order_by(ServiceOrder.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_my_orders_as_freelancer(self, freelancer: User) -> list[ServiceOrder]:
        result = await self.db.execute(
            select(ServiceOrder)
            .where(ServiceOrder.freelancer_id == freelancer.id)
            .options(selectinload(ServiceOrder.service))
            .order_by(ServiceOrder.created_at.desc())
        )
        return list(result.scalars().all())

    async def submit_requirements(
        self,
        order_id: uuid.UUID,
        client: User,
        answers: list[dict],
    ) -> ServiceOrder:
        """F3: Client submits structured answers. Transitions PENDING_REQUIREMENTS → IN_PROGRESS."""
        order = await self._get_order(order_id)
        if str(order.client_id) != str(client.id):
            raise ForbiddenError("Access denied")
        if order.status != ServiceOrderStatus.PENDING_REQUIREMENTS:
            raise BadRequestError(
                f"Requirements already submitted or order is not waiting for them "
                f"(status: {order.status.value})"
            )
        now = datetime.now(UTC)
        order.requirement_answers = answers
        order.requirements_submitted_at = now
        order.status = ServiceOrderStatus.IN_PROGRESS
        order.due_date = now + timedelta(days=order.delivery_days)
        await self.db.commit()

        asyncio.create_task(notify_background(
            user_id=order.freelancer_id,
            type=NotificationType.ORDER_REQUIREMENTS_SUBMITTED,
            title_ar="العميل أرسل متطلبات الطلب",
            title_en="Client submitted order requirements",
            message_ar="قدّم العميل إجاباته على أسئلة المتطلبات — يمكنك البدء بالعمل الآن.",
            message_en="The client answered the requirement questions — you can start work now.",
            link_type="service_order",
            link_id=str(order_id),
            actor_id=client.id,
        ))
        return order

    async def mark_delivered(
        self,
        order_id: uuid.UUID,
        freelancer: User,
        message: str,
        files: list[str] | None = None,
    ) -> ServiceOrder:
        """F4: Create a ServiceOrderDelivery record and mark order as DELIVERED."""
        order = await self._get_order(order_id)
        if str(order.freelancer_id) != str(freelancer.id):
            raise ForbiddenError("Access denied")
        if order.status not in (ServiceOrderStatus.IN_PROGRESS, ServiceOrderStatus.REVISION_REQUESTED):
            raise BadRequestError(
                "Order must be in progress or revision-requested to deliver"
            )

        from sqlalchemy import func as _func
        count_result = await self.db.execute(
            select(_func.count(ServiceOrderDelivery.id)).where(ServiceOrderDelivery.order_id == order_id)
        )
        revision_number = count_result.scalar_one() or 0

        delivery = ServiceOrderDelivery(
            order_id=order.id,
            message=message,
            files=files or [],
            revision_number=revision_number,
        )
        self.db.add(delivery)

        order.status = ServiceOrderStatus.DELIVERED
        order.delivered_at = datetime.now(UTC)
        await self.db.commit()

        asyncio.create_task(notify_background(
            user_id=order.client_id,
            type=NotificationType.ORDER_DELIVERED,
            title_ar="تم تسليم طلبك",
            title_en="Your order was delivered",
            message_ar="قدّم المستقل العمل المطلوب — راجعه وأبدِ رأيك.",
            message_en="The freelancer delivered your order — please review and respond.",
            link_type="service_order",
            link_id=str(order_id),
            actor_id=freelancer.id,
        ))
        return order

    async def list_deliveries(
        self, order_id: uuid.UUID, user: User
    ) -> list[ServiceOrderDelivery]:
        """List all deliveries for an order, oldest first (F4)."""
        order = await self._get_order(order_id)
        if str(order.client_id) != str(user.id) and str(order.freelancer_id) != str(user.id):
            raise ForbiddenError("Access denied")
        result = await self.db.execute(
            select(ServiceOrderDelivery)
            .where(ServiceOrderDelivery.order_id == order_id)
            .order_by(ServiceOrderDelivery.revision_number.asc(), ServiceOrderDelivery.created_at.asc())
        )
        return list(result.scalars().all())

    async def request_revision(self, order_id: uuid.UUID, client: User) -> ServiceOrder:
        order = await self._get_order(order_id)
        if str(order.client_id) != str(client.id):
            raise ForbiddenError("Access denied")
        if order.status != ServiceOrderStatus.DELIVERED:
            raise BadRequestError("Can only request revision on delivered orders")
        if order.revisions_remaining == 0:
            raise BadRequestError("No revisions remaining")
        order.status = ServiceOrderStatus.REVISION_REQUESTED
        if order.revisions_remaining > 0:
            order.revisions_remaining -= 1
        await self.db.commit()
        return order

    async def complete_order(self, order_id: uuid.UUID, client: User) -> ServiceOrder:
        order = await self._get_order(order_id)
        if str(order.client_id) != str(client.id):
            raise ForbiddenError("Access denied")
        if order.status not in (ServiceOrderStatus.DELIVERED,):
            raise BadRequestError("Order must be delivered to complete")
        order.status = ServiceOrderStatus.COMPLETED
        order.completed_at = datetime.now(UTC)
        await self.db.flush()

        # Release escrow via PaymentService so the lock, fee transaction, and
        # freelancer notification are handled consistently with contract milestones.
        escrow_result = await self.db.execute(
            select(Escrow.id).where(
                Escrow.service_order_id == order_id,
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        escrow_id = escrow_result.scalar_one_or_none()
        if escrow_id:
            from app.services.payment_service import PaymentService
            payment_svc = PaymentService(self.db)
            await payment_svc.release_escrow_by_id(escrow_id)
        else:
            logger.warning("complete_order: no funded escrow found for order %s", order_id)

        await self.db.commit()
        return order

    # ──────────────────────────────────────────
    # Dispute Management
    # ──────────────────────────────────────────

    async def raise_dispute(
        self,
        order_id: uuid.UUID,
        client: User,
        reason: str,
    ) -> ServiceOrder:
        """Client raises a dispute on an in-progress or delivered order."""
        order = await self._get_order(order_id)
        if str(order.client_id) != str(client.id):
            raise ForbiddenError("Only the client can raise a dispute")

        allowed_statuses = {
            ServiceOrderStatus.IN_PROGRESS,
            ServiceOrderStatus.DELIVERED,
            ServiceOrderStatus.REVISION_REQUESTED,
        }
        if order.status not in allowed_statuses:
            raise BadRequestError(
                f"Cannot raise a dispute on an order with status '{order.status.value}'. "
                "Disputes can only be raised on in-progress or delivered orders."
            )
        if order.status == ServiceOrderStatus.DISPUTED:
            raise BadRequestError("A dispute has already been raised for this order")

        order.status = ServiceOrderStatus.DISPUTED
        order.dispute_reason = reason
        order.dispute_opened_at = datetime.now(UTC)
        order.dispute_opened_by = client.id

        escrow_result = await self.db.execute(
            select(Escrow).where(
                Escrow.service_order_id == order_id,
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        escrow = escrow_result.scalar_one_or_none()
        if escrow:
            escrow.status = EscrowStatus.DISPUTED
            try:
                from app.middleware.monitoring import ESCROW_STATE_TRANSITIONS
                ESCROW_STATE_TRANSITIONS.labels(from_status="funded", to_status="disputed").inc()
            except Exception:
                pass

        await self.db.commit()
        await self.db.refresh(order)

        order_conv_result = await self.db.execute(
            select(Conversation).where(
                Conversation.order_id == order_id,
                Conversation.conversation_type == ConversationType.ORDER,
            )
        )
        order_conv = order_conv_result.scalar_one_or_none()
        if order_conv:
            from app.services.message_service import MessageService
            msg_svc = MessageService(self.db)
            await msg_svc.send_system_message(
                order_conv.id,
                f"⚠️ Dispute opened\nReason: {reason[:500]}\n"
                "The escrow has been frozen. An admin will review and resolve.",
            )
            await self.db.commit()

        asyncio.create_task(notify_background(
            user_id=order.freelancer_id,
            type=NotificationType.DISPUTE_OPENED,
            title_ar="نزاع تم فتحه على طلبك",
            title_en="A dispute was opened on your order",
            message_ar=f"قدّم العميل نزاعاً على الطلب. السبب: {reason[:200]}",
            message_en=f"The client raised a dispute on this order. Reason: {reason[:200]}",
            link_type="service_order",
            link_id=str(order_id),
            actor_id=client.id,
        ))
        admin_result = await self.db.execute(
            select(User).where(
                User.is_superuser == True,  # noqa: E712
                User.status == UserStatus.ACTIVE,
            )
        )
        for admin in admin_result.scalars().all():
            asyncio.create_task(notify_background(
                user_id=admin.id,
                type=NotificationType.DISPUTE_OPENED,
                title_ar="نزاع جديد مفتوح",
                title_en="New dispute opened",
                message_ar=f"فتح العميل نزاعاً على الطلب {order_id}. السبب: {reason[:200]}",
                message_en=f"Client raised a dispute on order {order_id}. Reason: {reason[:200]}",
                link_type="service_order",
                link_id=str(order_id),
                actor_id=client.id,
            ))

        return order

    async def resolve_dispute(
        self,
        order_id: uuid.UUID,
        admin: User,
        resolution: str,  # "release" | "refund"
        admin_note: str = "",
    ) -> ServiceOrder:
        """
        Admin resolves a disputed order.

        resolution="release" → escrow released to freelancer, order COMPLETED
        resolution="refund"  → escrow refunded to client, order CANCELLED
        """
        if resolution not in ("release", "refund"):
            raise BadRequestError("resolution must be 'release' or 'refund'")

        order = await self._get_order(order_id)
        if order.status != ServiceOrderStatus.DISPUTED:
            raise BadRequestError("Order is not in DISPUTED state")

        escrow_result = await self.db.execute(
            select(Escrow).where(
                Escrow.service_order_id == order_id,
                Escrow.status == EscrowStatus.DISPUTED,
            )
        )
        escrow = escrow_result.scalar_one_or_none()

        if resolution == "release":
            if escrow:
                escrow.status = EscrowStatus.FUNDED
                await self.db.flush()
                from app.services.payment_service import PaymentService  # noqa: PLC0415
                await PaymentService(self.db).release_escrow_by_id(escrow.id)
            order.status = ServiceOrderStatus.COMPLETED
            order.completed_at = datetime.now(UTC)
            order.dispute_resolution = "released_to_freelancer"
            client_msg_ar = "تم حل النزاع: تم تحرير المبلغ للمستقل."
            client_msg_en = "Dispute resolved: the amount was released to the freelancer."
            freelancer_msg_ar = "تم حل النزاع لصالحك: تم تحرير المبلغ."
            freelancer_msg_en = "Dispute resolved in your favour — payment released."
        else:  # refund
            if escrow:
                from app.services.payment_service import PaymentService  # noqa: PLC0415
                await PaymentService(self.db).refund_escrow_by_service_order(order_id)
            order.status = ServiceOrderStatus.CANCELLED
            order.cancellation_reason = f"Dispute resolved: refund to client. {admin_note}"
            order.cancelled_by = admin.id
            order.dispute_resolution = "refunded_to_client"
            client_msg_ar = "تم حل النزاع: تم استرداد المبلغ إليك."
            client_msg_en = "Dispute resolved: refund issued to you."
            freelancer_msg_ar = "تم حل النزاع: تم إرجاع المبلغ للعميل."
            freelancer_msg_en = "Dispute resolved: the amount was refunded to the client."

        order.dispute_resolved_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(order)

        order_conv_result = await self.db.execute(
            select(Conversation).where(
                Conversation.order_id == order_id,
                Conversation.conversation_type == ConversationType.ORDER,
            )
        )
        order_conv = order_conv_result.scalar_one_or_none()
        if order_conv:
            from app.services.message_service import MessageService
            msg_svc = MessageService(self.db)
            resolution_text = (
                "released to freelancer" if resolution == "release"
                else "refunded to client"
            )
            note_suffix = f"\nAdmin note: {admin_note}" if admin_note else ""
            await msg_svc.send_system_message(
                order_conv.id,
                f"✅ Dispute resolved\nOutcome: {resolution_text}{note_suffix}",
            )
            await self.db.commit()

        # Notify both parties
        for user_id, msg_ar, msg_en in [
            (order.client_id, client_msg_ar, client_msg_en),
            (order.freelancer_id, freelancer_msg_ar, freelancer_msg_en),
        ]:
            asyncio.create_task(notify_background(
                user_id=user_id,
                type=NotificationType.DISPUTE_RESOLVED,
                title_ar="تم حل النزاع",
                title_en="Dispute resolved",
                message_ar=msg_ar,
                message_en=msg_en,
                link_type="service_order",
                link_id=str(order_id),
                actor_id=admin.id,
            ))

        return order

    async def list_disputed_orders(self) -> list[ServiceOrder]:
        """Admin: list all orders currently in DISPUTED status."""
        result = await self.db.execute(
            select(ServiceOrder)
            .where(ServiceOrder.status == ServiceOrderStatus.DISPUTED)
            .options(
                selectinload(ServiceOrder.service),
            )
            .order_by(ServiceOrder.dispute_opened_at.asc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    async def _load_service(self, service_id: uuid.UUID) -> Optional[Service]:
        result = await self.db.execute(
            select(Service)
            .where(Service.id == service_id)
            .options(
                selectinload(Service.packages),
                selectinload(Service.freelancer),
                selectinload(Service.category),
                selectinload(Service.subcategory),
            )
        )
        return result.scalar_one_or_none()

    async def _load_service_by_slug(self, slug: str) -> Optional[Service]:
        result = await self.db.execute(
            select(Service)
            .where(Service.slug == slug)
            .options(
                selectinload(Service.packages),
                selectinload(Service.freelancer),
                selectinload(Service.category),
                selectinload(Service.subcategory),
            )
        )
        return result.scalar_one_or_none()

    async def _unique_slug(self, base: str, exclude_id: Optional[uuid.UUID] = None) -> str:
        slug = base
        counter = 1
        while True:
            q = select(Service.id).where(Service.slug == slug)
            if exclude_id:
                q = q.where(Service.id != exclude_id)
            existing = (await self.db.execute(q)).scalar_one_or_none()
            if not existing:
                return slug
            slug = f"{base}-{counter}"
            counter += 1

    async def _get_order(self, order_id: uuid.UUID) -> ServiceOrder:
        order = await self.db.get(ServiceOrder, order_id)
        if not order:
            raise NotFoundError("Order")
        return order
