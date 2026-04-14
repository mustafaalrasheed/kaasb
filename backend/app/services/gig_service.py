"""
Kaasb Platform - Gig Service
Business logic for the Fiverr-style gig marketplace.
"""

import asyncio
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ExternalServiceError, ForbiddenError, NotFoundError
from app.models.gig import (
    Category,
    Gig,
    GigOrder,
    GigOrderStatus,
    GigPackage,
    GigStatus,
)
from app.models.notification import NotificationType
from app.models.payment import (
    Escrow,
    EscrowStatus,
    PaymentProvider,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.models.user import User, UserRole
from app.schemas.gig import (
    GigCreate,
    GigOrderCreate,
    GigSearchParams,
    GigUpdate,
)
from app.services.base import BaseService
from app.services.notification_service import notify
from app.services.qi_card_client import USD_TO_IQD, QiCardClient, QiCardError

logger = logging.getLogger(__name__)


def _slugify(text: str, suffix: str = "") -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug[:100]
    if suffix:
        slug = f"{slug}-{suffix}"
    return slug


class GigService(BaseService):
    """Service for gig marketplace operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    # ──────────────────────────────────────────
    # Categories
    # ──────────────────────────────────────────

    async def list_categories(self) -> list[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.is_active == True)  # noqa: E712
            .options(selectinload(Category.subcategories))
            .order_by(Category.sort_order)
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Gig CRUD
    # ──────────────────────────────────────────

    async def create_gig(self, freelancer: User, data: GigCreate) -> Gig:
        if freelancer.primary_role not in (UserRole.FREELANCER, UserRole.ADMIN):
            raise ForbiddenError("Only freelancers can create gigs")

        # Verify category exists
        cat = await self.db.get(Category, data.category_id)
        if not cat:
            raise NotFoundError("Category")

        # Generate unique slug
        base_slug = _slugify(data.title)
        slug = await self._unique_slug(base_slug)

        gig = Gig(
            freelancer_id=freelancer.id,
            title=data.title,
            slug=slug,
            description=data.description,
            category_id=data.category_id,
            subcategory_id=data.subcategory_id,
            tags=data.tags,
            status=GigStatus.PENDING_REVIEW,
        )
        self.db.add(gig)
        await self.db.flush()  # get gig.id

        # Create packages
        for pkg_data in data.packages:
            pkg = GigPackage(
                gig_id=gig.id,
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
        await self.db.refresh(gig)

        # Collect admin IDs and gig data BEFORE _load_gig so notify tasks are
        # scheduled after the load completes (avoids concurrent AsyncSession use).
        admin_result = await self.db.execute(
            select(User).where(
                User.is_superuser == True,  # noqa: E712
                User.status == "active",
            )
        )
        admin_ids = [admin.id for admin in admin_result.scalars().all()]
        gig_title = gig.title
        gig_id_str = str(gig.id)
        freelancer_username = freelancer.username

        # Eager-load relationships for response BEFORE scheduling background tasks.
        # asyncio.create_task shares self.db — concurrent use of the same AsyncSession
        # across coroutines causes a 500. Load first, notify after.
        loaded_gig = await self._load_gig(gig.id)

        for admin_id in admin_ids:
            asyncio.create_task(notify(
                self.db,
                user_id=admin_id,
                type=NotificationType.GIG_SUBMITTED,
                title="New gig pending review",
                message=f'"{gig_title}" by {freelancer_username} is awaiting approval.',
                link_type="gig",
                link_id=gig_id_str,
            ))

        return loaded_gig  # type: ignore[return-value]

    async def get_gig_by_slug(self, slug: str) -> Gig:
        gig = await self._load_gig_by_slug(slug)
        if not gig:
            raise NotFoundError("Gig")
        if gig.status != GigStatus.ACTIVE:
            raise NotFoundError("Gig")
        # Increment impressions (fire and forget — don't await commit)
        await self.db.execute(
            update(Gig).where(Gig.id == gig.id).values(impressions=Gig.impressions + 1)
        )
        await self.db.commit()
        return gig

    async def get_gig_by_id_for_owner(self, gig_id: uuid.UUID, user: User) -> Gig:
        """Get any gig (any status) for the owner or admin."""
        gig = await self._load_gig(gig_id)
        if not gig:
            raise NotFoundError("Gig")
        if gig.freelancer_id != user.id and user.primary_role != UserRole.ADMIN:
            raise ForbiddenError("Access denied")
        return gig

    async def update_gig(self, gig_id: uuid.UUID, user: User, data: GigUpdate) -> Gig:
        gig = await self.get_gig_by_id_for_owner(gig_id, user)

        if data.title is not None:
            gig.title = data.title
            gig.slug = await self._unique_slug(_slugify(data.title), exclude_id=gig.id)
        if data.description is not None:
            gig.description = data.description
        if data.category_id is not None:
            gig.category_id = data.category_id
        if data.subcategory_id is not None:
            gig.subcategory_id = data.subcategory_id
        if data.tags is not None:
            gig.tags = data.tags

        if data.packages is not None:
            # Replace all packages
            for old_pkg in gig.packages:
                await self.db.delete(old_pkg)
            await self.db.flush()
            for pkg_data in data.packages:
                pkg = GigPackage(
                    gig_id=gig.id,
                    tier=pkg_data.tier,
                    name=pkg_data.name,
                    description=pkg_data.description,
                    price=pkg_data.price,
                    delivery_days=pkg_data.delivery_days,
                    revisions=pkg_data.revisions,
                    features=pkg_data.features,
                )
                self.db.add(pkg)

        # Re-submit for review when freelancer edits
        if gig.status in (GigStatus.ACTIVE, GigStatus.NEEDS_REVISION):
            gig.status = GigStatus.PENDING_REVIEW
            gig.revision_note = None  # clear previous revision note on resubmit

        await self.db.commit()
        return await self._load_gig(gig.id)  # type: ignore[return-value]

    async def delete_gig(self, gig_id: uuid.UUID, user: User) -> None:
        gig = await self.get_gig_by_id_for_owner(gig_id, user)
        if gig.orders_count > 0:
            raise BadRequestError("Cannot delete a gig that has orders — archive it instead")
        await self.db.delete(gig)
        await self.db.commit()

    async def pause_gig(self, gig_id: uuid.UUID, user: User) -> Gig:
        gig = await self.get_gig_by_id_for_owner(gig_id, user)
        if gig.status not in (GigStatus.ACTIVE,):
            raise BadRequestError("Only active gigs can be paused")
        gig.status = GigStatus.PAUSED
        await self.db.commit()
        return await self._load_gig(gig.id)  # type: ignore[return-value]

    async def resume_gig(self, gig_id: uuid.UUID, user: User) -> Gig:
        gig = await self.get_gig_by_id_for_owner(gig_id, user)
        if gig.status != GigStatus.PAUSED:
            raise BadRequestError("Only paused gigs can be resumed")
        gig.status = GigStatus.ACTIVE
        await self.db.commit()
        return await self._load_gig(gig.id)  # type: ignore[return-value]

    # ──────────────────────────────────────────
    # Search / Listing
    # ──────────────────────────────────────────

    async def search_gigs(
        self, params: GigSearchParams
    ) -> tuple[list[Gig], int]:
        """Returns (gigs, total_count) for the given search params."""
        q = (
            select(Gig)
            .where(Gig.status == GigStatus.ACTIVE)
            .options(
                selectinload(Gig.freelancer),
                selectinload(Gig.packages),
                selectinload(Gig.category),
            )
        )

        if params.q:
            term = f"%{params.q}%"
            q = q.where(
                or_(
                    Gig.title.ilike(term),
                    Gig.description.ilike(term),
                )
            )
        if params.category_id:
            q = q.where(Gig.category_id == params.category_id)
        if params.subcategory_id:
            q = q.where(Gig.subcategory_id == params.subcategory_id)

        # Count total
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Sorting
        sort_map = {
            "newest": Gig.created_at.desc(),
            "rating": Gig.avg_rating.desc(),
            "orders": Gig.orders_count.desc(),
        }
        order_col = sort_map.get(params.sort_by, Gig.orders_count.desc())
        q = q.order_by(order_col)

        # Pagination
        offset = (params.page - 1) * params.page_size
        q = q.offset(offset).limit(params.page_size)

        result = await self.db.execute(q)
        gigs = list(result.scalars().all())
        return gigs, total

    async def list_my_gigs(self, freelancer: User) -> list[Gig]:
        result = await self.db.execute(
            select(Gig)
            .where(Gig.freelancer_id == freelancer.id)
            .options(selectinload(Gig.packages), selectinload(Gig.category))
            .order_by(Gig.created_at.desc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Admin Review
    # ──────────────────────────────────────────

    async def approve_gig(self, gig_id: uuid.UUID, admin: User) -> Gig:
        gig = await self._load_gig(gig_id)
        if not gig:
            raise NotFoundError("Gig")
        if gig.status not in (GigStatus.PENDING_REVIEW, GigStatus.NEEDS_REVISION):
            raise BadRequestError(f"Cannot approve a gig with status '{gig.status.value}'.")
        # Capture notification params before commit (ORM object expires after commit)
        freelancer_id = gig.freelancer_id
        gig_title = gig.title
        gig_id_str = str(gig.id)

        gig.status = GigStatus.ACTIVE
        gig.rejection_reason = None
        gig.reviewed_by_id = admin.id
        gig.reviewed_at = datetime.now(UTC)
        await self.db.commit()

        # Reload the updated gig BEFORE scheduling the background notification.
        # asyncio.create_task shares self.db — running _load_gig() concurrently
        # with notify() on the same AsyncSession causes a 500. Load first, notify after.
        updated_gig = await self._load_gig(gig_id)

        asyncio.create_task(notify(
            self.db,
            user_id=freelancer_id,
            type=NotificationType.GIG_APPROVED,
            title="Your gig was approved",
            message=f'Your gig "{gig_title}" is now live and visible to clients.',
            link_type="gig",
            link_id=gig_id_str,
        ))
        return updated_gig  # type: ignore[return-value]

    async def request_gig_revision(self, gig_id: uuid.UUID, note: str, admin: User) -> Gig:
        gig = await self._load_gig(gig_id)
        if not gig:
            raise NotFoundError("Gig")
        if gig.status not in (GigStatus.PENDING_REVIEW, GigStatus.NEEDS_REVISION, GigStatus.ACTIVE):
            raise BadRequestError(f"Cannot request revision on a gig with status '{gig.status.value}'.")
        freelancer_id = gig.freelancer_id
        gig_title = gig.title
        gig_id_str = str(gig.id)

        gig.status = GigStatus.NEEDS_REVISION
        gig.revision_note = note
        gig.reviewed_by_id = admin.id
        gig.reviewed_at = datetime.now(UTC)
        await self.db.commit()

        updated_gig = await self._load_gig(gig_id)

        asyncio.create_task(notify(
            self.db,
            user_id=freelancer_id,
            type=NotificationType.GIG_NEEDS_REVISION,
            title="Your gig needs edits before it can go live",
            message=f'Your gig "{gig_title}" needs changes: {note}',
            link_type="gig",
            link_id=gig_id_str,
        ))
        return updated_gig  # type: ignore[return-value]

    async def reject_gig(self, gig_id: uuid.UUID, reason: str, admin: User) -> Gig:
        gig = await self._load_gig(gig_id)
        if not gig:
            raise NotFoundError("Gig")
        if gig.status == GigStatus.REJECTED:
            return gig  # Already rejected — idempotent
        if gig.status not in (GigStatus.PENDING_REVIEW, GigStatus.NEEDS_REVISION, GigStatus.ACTIVE):
            raise BadRequestError(f"Cannot reject a gig with status '{gig.status.value}'.")
        freelancer_id = gig.freelancer_id
        gig_title = gig.title
        gig_id_str = str(gig.id)

        gig.status = GigStatus.REJECTED
        gig.rejection_reason = reason
        gig.revision_note = None
        gig.reviewed_by_id = admin.id
        gig.reviewed_at = datetime.now(UTC)
        await self.db.commit()

        updated_gig = await self._load_gig(gig_id)

        asyncio.create_task(notify(
            self.db,
            user_id=freelancer_id,
            type=NotificationType.GIG_REJECTED,
            title="Your gig was rejected",
            message=f'Your gig "{gig_title}" was rejected. Reason: {reason}',
            link_type="gig",
            link_id=gig_id_str,
        ))
        return updated_gig  # type: ignore[return-value]

    async def list_pending_gigs(self) -> list[Gig]:
        result = await self.db.execute(
            select(Gig)
            .where(Gig.status.in_([GigStatus.PENDING_REVIEW, GigStatus.NEEDS_REVISION]))
            .options(
                selectinload(Gig.freelancer),
                selectinload(Gig.packages),
                selectinload(Gig.category),
                selectinload(Gig.subcategory),
            )
            .order_by(Gig.created_at.asc())
        )
        return list(result.scalars().all())

    # ──────────────────────────────────────────
    # Orders
    # ──────────────────────────────────────────

    async def place_order(self, client: User, data: GigOrderCreate) -> tuple[GigOrder, str | None]:
        """
        Create a gig order and initiate Qi Card payment.

        Returns (order, payment_url). If Qi Card is not configured (sandbox/dev),
        payment_url is the mock URL. Escrow stays PENDING until payment confirmed.
        """
        if client.primary_role == UserRole.ADMIN:
            raise ForbiddenError("Admins cannot place orders")

        # Load gig + package
        gig = await self._load_gig(data.gig_id)
        if not gig or gig.status != GigStatus.ACTIVE:
            raise NotFoundError("Gig")

        if str(gig.freelancer_id) == str(client.id):
            raise BadRequestError("Cannot order your own gig")

        pkg = next((p for p in gig.packages if str(p.id) == str(data.package_id)), None)
        if not pkg:
            raise NotFoundError("Package")

        settings = get_settings()
        fee_rate = Decimal(str(settings.PLATFORM_FEE_PERCENT)) / Decimal("100")
        price_d = Decimal(str(float(pkg.price)))
        platform_fee_d = (price_d * fee_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        freelancer_amount_d = (price_d - platform_fee_d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        due = datetime.now(UTC) + timedelta(days=pkg.delivery_days)

        order = GigOrder(
            gig_id=gig.id,
            package_id=pkg.id,
            client_id=client.id,
            freelancer_id=gig.freelancer_id,
            status=GigOrderStatus.PENDING,
            requirements=data.requirements,
            price_paid=float(pkg.price),
            delivery_days=pkg.delivery_days,
            revisions_remaining=pkg.revisions,
            due_date=due,
        )
        self.db.add(order)

        # Increment order count on gig
        await self.db.execute(
            update(Gig).where(Gig.id == gig.id).values(orders_count=Gig.orders_count + 1)
        )

        # Flush to get order.id before initiating payment
        await self.db.flush()

        # Initiate Qi Card payment (price is stored in IQD)
        order_ref = f"gig-order-{order.id}"
        base = f"https://{settings.DOMAIN}"
        payment_url: str | None = None

        try:
            qi_card = QiCardClient()
            # price is IQD; convert to USD for QiCardClient which converts back
            amount_usd = float(price_d) / USD_TO_IQD
            qi_result = await qi_card.create_payment(
                amount_usd=amount_usd,
                order_id=order_ref,
                success_url=f"{base}/api/v1/payments/qi-card/success",
                failure_url=f"{base}/api/v1/payments/qi-card/failure",
                cancel_url=f"{base}/api/v1/payments/qi-card/cancel",
            )
            payment_url = qi_result.get("link")
        except QiCardError as e:
            logger.error("Qi Card error during gig order %s: %s", order.id, e)
            # Roll back so order is not half-created without payment
            await self.db.rollback()
            raise ExternalServiceError("Payment gateway error. Please try again later.") from e

        # Create transaction record
        txn = Transaction(
            transaction_type=TransactionType.ESCROW_FUND,
            status=TransactionStatus.PENDING,
            amount=float(price_d),
            currency=settings.QI_CARD_CURRENCY,
            platform_fee=float(platform_fee_d),
            net_amount=float(freelancer_amount_d),
            payer_id=client.id,
            payee_id=gig.freelancer_id,
            provider=PaymentProvider.QI_CARD,
            external_transaction_id=order_ref,
            description=f"Gig order: {gig.title[:100]}",
        )
        self.db.add(txn)
        await self.db.flush()

        # Create escrow in PENDING state (moves to FUNDED after payment confirmation)
        escrow = Escrow(
            amount=float(price_d),
            platform_fee=float(platform_fee_d),
            freelancer_amount=float(freelancer_amount_d),
            currency=settings.QI_CARD_CURRENCY,
            status=EscrowStatus.PENDING,
            gig_order_id=order.id,
            client_id=client.id,
            freelancer_id=gig.freelancer_id,
            funding_transaction_id=txn.id,
        )
        self.db.add(escrow)

        await self.db.commit()
        await self.db.refresh(order)
        return order, payment_url

    async def get_my_orders_as_client(self, client: User) -> list[GigOrder]:
        result = await self.db.execute(
            select(GigOrder)
            .where(GigOrder.client_id == client.id)
            .options(selectinload(GigOrder.gig))
            .order_by(GigOrder.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_my_orders_as_freelancer(self, freelancer: User) -> list[GigOrder]:
        result = await self.db.execute(
            select(GigOrder)
            .where(GigOrder.freelancer_id == freelancer.id)
            .options(selectinload(GigOrder.gig))
            .order_by(GigOrder.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_delivered(self, order_id: uuid.UUID, freelancer: User) -> GigOrder:
        order = await self._get_order(order_id)
        if str(order.freelancer_id) != str(freelancer.id):
            raise ForbiddenError("Access denied")
        if order.status != GigOrderStatus.IN_PROGRESS:
            raise BadRequestError("Order must be in progress to mark delivered")
        order.status = GigOrderStatus.DELIVERED
        order.delivered_at = datetime.now(UTC)
        await self.db.commit()
        return order

    async def request_revision(self, order_id: uuid.UUID, client: User) -> GigOrder:
        order = await self._get_order(order_id)
        if str(order.client_id) != str(client.id):
            raise ForbiddenError("Access denied")
        if order.status != GigOrderStatus.DELIVERED:
            raise BadRequestError("Can only request revision on delivered orders")
        if order.revisions_remaining == 0:
            raise BadRequestError("No revisions remaining")
        order.status = GigOrderStatus.REVISION_REQUESTED
        if order.revisions_remaining > 0:
            order.revisions_remaining -= 1
        await self.db.commit()
        return order

    async def complete_order(self, order_id: uuid.UUID, client: User) -> GigOrder:
        order = await self._get_order(order_id)
        if str(order.client_id) != str(client.id):
            raise ForbiddenError("Access denied")
        if order.status not in (GigOrderStatus.DELIVERED,):
            raise BadRequestError("Order must be delivered to complete")
        order.status = GigOrderStatus.COMPLETED
        order.completed_at = datetime.now(UTC)

        # Release escrow to freelancer
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.gig_order_id == order_id,
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        escrow = result.scalar_one_or_none()
        if escrow:
            settings = get_settings()
            escrow.status = EscrowStatus.RELEASED
            escrow.released_at = datetime.now(UTC)

            # Record the release transaction
            release_txn = Transaction(
                transaction_type=TransactionType.ESCROW_RELEASE,
                status=TransactionStatus.COMPLETED,
                amount=escrow.freelancer_amount,
                currency=settings.QI_CARD_CURRENCY,
                platform_fee=0,
                net_amount=escrow.freelancer_amount,
                payer_id=order.client_id,
                payee_id=order.freelancer_id,
                provider=PaymentProvider.QI_CARD,
                description=f"Escrow released for gig order {order_id}",
                completed_at=datetime.now(UTC),
            )
            self.db.add(release_txn)
            await self.db.flush()
            escrow.release_transaction_id = release_txn.id
        else:
            logger.warning("complete_order: no funded escrow found for order %s", order_id)

        await self.db.commit()
        return order

    # ──────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────

    async def _load_gig(self, gig_id: uuid.UUID) -> Optional[Gig]:
        result = await self.db.execute(
            select(Gig)
            .where(Gig.id == gig_id)
            .options(
                selectinload(Gig.packages),
                selectinload(Gig.freelancer),
                selectinload(Gig.category),
                selectinload(Gig.subcategory),
            )
        )
        return result.scalar_one_or_none()

    async def _load_gig_by_slug(self, slug: str) -> Optional[Gig]:
        result = await self.db.execute(
            select(Gig)
            .where(Gig.slug == slug)
            .options(
                selectinload(Gig.packages),
                selectinload(Gig.freelancer),
                selectinload(Gig.category),
                selectinload(Gig.subcategory),
            )
        )
        return result.scalar_one_or_none()

    async def _unique_slug(self, base: str, exclude_id: Optional[uuid.UUID] = None) -> str:
        slug = base
        counter = 1
        while True:
            q = select(Gig.id).where(Gig.slug == slug)
            if exclude_id:
                q = q.where(Gig.id != exclude_id)
            existing = (await self.db.execute(q)).scalar_one_or_none()
            if not existing:
                return slug
            slug = f"{base}-{counter}"
            counter += 1

    async def _get_order(self, order_id: uuid.UUID) -> GigOrder:
        order = await self.db.get(GigOrder, order_id)
        if not order:
            raise NotFoundError("Order")
        return order
