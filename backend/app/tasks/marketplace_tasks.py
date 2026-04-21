"""
Kaasb Platform - Marketplace Background Tasks
============================================
Runs as a daily cron job (suggested: 02:00 UTC) to keep denormalized
marketplace data consistent with actual order/review activity.

Covers:
  - F1: Expire buyer requests past their expires_at
  - F2: Recalculate seller levels for all freelancers
  - F4: Auto-complete delivered orders after 3 days without client action
  - F7: Refresh service rank_score for all active services

Run from the project root:
    python -m app.tasks.marketplace_tasks

Or via cron (add to /etc/cron.d/kaasb):
    0 2 * * * root cd /app && python -m app.tasks.marketplace_tasks >> /var/log/kaasb/marketplace_tasks.log 2>&1
"""

import asyncio
import logging
import math
import sys
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [marketplace_tasks] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Seller level thresholds
_LEVEL_1 = {
    "min_orders": 10,
    "min_rating": 4.0,
    "min_completion": 0.90,
    "min_response": 0.80,
    "min_months": 0,
}
_LEVEL_2 = {
    "min_orders": 50,
    "min_rating": 4.5,
    "min_completion": 0.95,
    "min_response": 0.90,
    "min_months": 2,
}
_TOP_RATED = {
    "min_orders": 100,
    "min_rating": 4.8,
    "min_completion": 0.98,
    "min_response": 0.95,
    "min_months": 6,
}


async def expire_buyer_requests(db: AsyncSession) -> int:
    """Set status=expired on OPEN buyer requests past their expires_at."""
    from app.models.buyer_request import BuyerRequest, BuyerRequestStatus
    result = await db.execute(
        update(BuyerRequest)
        .where(
            BuyerRequest.status == BuyerRequestStatus.OPEN,
            BuyerRequest.expires_at < datetime.now(UTC),
        )
        .values(status=BuyerRequestStatus.EXPIRED)
    )
    count = result.rowcount
    await db.commit()
    logger.info("Buyer requests expired: %d", count)
    return count


async def recalculate_seller_levels(db: AsyncSession) -> dict[str, int]:
    """
    Recalculate seller_level for all freelancers based on their completed orders,
    avg_rating, completion_rate, response_rate, and account age.

    Returns summary dict of level transitions.
    """
    from app.models.notification import NotificationType
    from app.models.service import ServiceOrder, ServiceOrderStatus
    from app.models.user import SellerLevel, User, UserRole
    from app.services.notification_service import notify_background

    summary = {"upgraded": 0, "downgraded": 0, "unchanged": 0}
    now = datetime.now(UTC)

    # Human-readable labels for notification copy.
    level_labels_ar = {
        SellerLevel.LEVEL_1: "المستوى الأول",
        SellerLevel.LEVEL_2: "المستوى الثاني",
        SellerLevel.TOP_RATED: "الأعلى تقييماً",
        SellerLevel.NEW_SELLER: "بائع جديد",
    }

    freelancers_result = await db.execute(
        select(User).where(User.primary_role == UserRole.FREELANCER)
    )
    freelancers = list(freelancers_result.scalars().all())

    upgraded_users: list[tuple[uuid.UUID, SellerLevel]] = []

    for user in freelancers:
        completed_result = await db.execute(
            select(func.count(ServiceOrder.id)).where(
                ServiceOrder.freelancer_id == user.id,
                ServiceOrder.status == ServiceOrderStatus.COMPLETED,
            )
        )
        completed_orders = completed_result.scalar_one() or 0

        total_result = await db.execute(
            select(func.count(ServiceOrder.id)).where(
                ServiceOrder.freelancer_id == user.id,
                ServiceOrder.status.notin_([ServiceOrderStatus.PENDING]),
            )
        )
        total_orders = total_result.scalar_one() or 0

        completion_rate = completed_orders / total_orders if total_orders > 0 else 0.0
        avg_rating = float(user.avg_rating or 0.0)
        months_active = max(0, (now - user.created_at.replace(tzinfo=UTC)).days // 30)

        # Response rate: approximate from stored field (defaults 0, updated by F6)
        response_rate = float(user.response_rate or 0.0)

        # Determine new level (highest threshold that passes, else new_seller)
        def qualifies(
            thresholds: dict,
            _co: float = completed_orders,
            _ar: float = avg_rating,
            _cr: float = completion_rate,
            _rr: float = response_rate,
            _ma: int = months_active,
        ) -> bool:
            return (
                _co >= thresholds["min_orders"]
                and _ar >= thresholds["min_rating"]
                and _cr >= thresholds["min_completion"]
                and _rr >= thresholds["min_response"]
                and _ma >= thresholds["min_months"]
            )

        # TOP_RATED requires manual admin review — only keep, never auto-grant
        if user.seller_level == SellerLevel.TOP_RATED:
            new_level = SellerLevel.TOP_RATED  # manual only
        elif qualifies(_LEVEL_2):
            new_level = SellerLevel.LEVEL_2
        elif qualifies(_LEVEL_1):
            new_level = SellerLevel.LEVEL_1
        else:
            new_level = SellerLevel.NEW_SELLER

        old_level = user.seller_level
        user.total_completed_orders = completed_orders
        user.completion_rate = completion_rate
        user.seller_level = new_level
        user.level_updated_at = now

        if new_level != old_level:
            if list(SellerLevel).index(new_level) > list(SellerLevel).index(old_level):
                summary["upgraded"] += 1
                upgraded_users.append((user.id, new_level))
            else:
                summary["downgraded"] += 1
        else:
            summary["unchanged"] += 1

    await db.commit()
    logger.info(
        "Seller levels recalculated: %d upgraded, %d downgraded, %d unchanged",
        summary["upgraded"], summary["downgraded"], summary["unchanged"],
    )

    # Notify users who moved up a level. We only notify on upgrade (never on
    # downgrade) — demotions are silent to avoid demoralising freelancers, and
    # will eventually be visible on their profile anyway.
    for user_id, new_level in upgraded_users:
        label = level_labels_ar.get(new_level, new_level.value)
        asyncio.create_task(
            notify_background(
                user_id=user_id,
                type=NotificationType.SELLER_LEVEL_UPGRADED,
                title="تمت ترقية مستوى حسابك",
                message=f"تهانينا — تمت ترقيتك إلى: {label}",
                link_type=None,
                link_id=None,
            )
        )

    return summary


async def auto_complete_delivered_orders(db: AsyncSession) -> int:
    """
    Auto-complete orders that have been in DELIVERED status for > 3 days
    without client action. Releases escrow to the freelancer.
    """
    from app.models.notification import NotificationType
    from app.models.service import ServiceOrder, ServiceOrderStatus
    from app.services.notification_service import notify_background

    cutoff = datetime.now(UTC) - timedelta(days=3)
    result = await db.execute(
        select(ServiceOrder).where(
            ServiceOrder.status == ServiceOrderStatus.DELIVERED,
            ServiceOrder.delivered_at <= cutoff,
        )
    )
    orders = list(result.scalars().all())
    completed = 0

    for order in orders:
        try:
            order.status = ServiceOrderStatus.COMPLETED
            order.completed_at = datetime.now(UTC)
            await db.flush()

            from sqlalchemy import select as _select

            from app.models.payment import Escrow, EscrowStatus
            escrow_result = await db.execute(
                _select(Escrow).where(
                    Escrow.service_order_id == order.id,
                    Escrow.status == EscrowStatus.FUNDED,
                )
            )
            escrow = escrow_result.scalar_one_or_none()
            if escrow:
                from app.services.payment_service import PaymentService
                await PaymentService(db).release_escrow_by_id(escrow.id)

            await db.commit()
            completed += 1

            asyncio.create_task(notify_background(
                user_id=order.client_id,
                type=NotificationType.ORDER_AUTO_COMPLETED,
                title="تم إغلاق الطلب تلقائياً",
                message="تم إغلاق الطلب تلقائياً بعد 3 أيام من التسليم دون رد.",
                link_type="service_order",
                link_id=str(order.id),
            ))
        except Exception as exc:
            logger.exception("Failed to auto-complete order %s: %s", order.id, exc)
            await db.rollback()

    logger.info("Orders auto-completed: %d", completed)
    return completed


async def refresh_service_rank_scores(db: AsyncSession) -> int:
    """
    Recalculate rank_score for all active services.
    Score is a weighted sum (0–100) of:
      conversion_score  : orders / impressions
      review_score      : avg_rating * log(reviews + 1)
      freshness_score   : decaying factor based on days since published
      completion_score  : freelancer completion rate
      seller_level_bonus: 0 / 0.5 / 1.0 / 1.5 per level
    """
    from app.models.service import Service, ServiceStatus
    from app.models.user import SellerLevel, User

    result = await db.execute(
        select(Service, User)
        .join(User, Service.freelancer_id == User.id)
        .where(Service.status == ServiceStatus.ACTIVE)
    )
    rows = result.all()
    updated = 0
    now = datetime.now(UTC)

    level_bonus = {
        SellerLevel.NEW_SELLER: 0.0,
        SellerLevel.LEVEL_1: 0.5,
        SellerLevel.LEVEL_2: 1.0,
        SellerLevel.TOP_RATED: 1.5,
    }

    for service, freelancer in rows:
        impressions = max(service.impressions or 0, 1)
        orders = service.orders_count or 0
        avg_rating = float(service.avg_rating or 0.0)
        reviews = service.reviews_count or 0

        conversion = min(orders / impressions, 1.0) * 25.0

        review_raw = avg_rating * math.log(reviews + 1)
        review_score = min(review_raw / (5.0 * math.log(101)), 1.0) * 30.0

        days_old = (now - service.created_at.replace(tzinfo=UTC)).days
        freshness = math.exp(-days_old / 90.0) * 20.0

        completion = float(freelancer.completion_rate or 0.0) * 20.0

        bonus = level_bonus.get(freelancer.seller_level, 0.0) * (5.0 / 1.5)

        rank = round(conversion + review_score + freshness + completion + bonus, 2)

        await db.execute(
            update(Service)
            .where(Service.id == service.id)
            .values(rank_score=rank, rank_updated_at=now)
            .execution_options(synchronize_session=False)
        )
        updated += 1

    await db.commit()
    logger.info("Service rank scores refreshed: %d services", updated)
    return updated


refresh_gig_rank_scores = refresh_service_rank_scores


async def flag_stuck_pending_transactions(
    db: AsyncSession, min_age_minutes: int = 30
) -> int:
    """
    Count PENDING Transactions older than `min_age_minutes`.

    These are the canonical signal for "Qi Card redirect succeeded on the
    user's browser but the success webhook never reached Kaasb" — the money
    may already be on the merchant balance while Kaasb still thinks the
    payment is in progress. Counted here so the daily task updates the
    Prometheus gauge; admins see the queue via GET /admin/payments/stuck-pending
    and resolve each one manually until the v1 3DS status API is wired up
    (P0-3 in the payments plan).
    """
    from app.models.payment import Transaction, TransactionStatus

    cutoff = datetime.now(UTC) - timedelta(minutes=min_age_minutes)
    result = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.status == TransactionStatus.PENDING,
            Transaction.created_at < cutoff,
        )
    )
    count = int(result.scalar() or 0)

    if count:
        logger.warning(
            "payments: %d PENDING transactions older than %dmin — likely need "
            "manual reconciliation against Qi Card merchant dashboard",
            count, min_age_minutes,
        )

    try:
        from app.middleware.monitoring import STUCK_PENDING_TRANSACTIONS
        STUCK_PENDING_TRANSACTIONS.set(count)
    except Exception:
        logger.debug("metrics: stuck-pending gauge emit failed", exc_info=True)

    return count


async def run_all(db: AsyncSession) -> dict:
    summary: dict = {}
    summary["buyer_requests_expired"] = await expire_buyer_requests(db)
    summary["seller_levels"] = await recalculate_seller_levels(db)
    summary["orders_auto_completed"] = await auto_complete_delivered_orders(db)
    summary["service_rank_scores_updated"] = await refresh_service_rank_scores(db)
    summary["stuck_pending_transactions"] = await flag_stuck_pending_transactions(db)
    return summary


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(  # type: ignore[call-overload]
        engine, class_=AsyncSession, expire_on_commit=False
    )

    logger.info("Marketplace tasks starting")
    async with AsyncSessionLocal() as db:
        try:
            summary = await run_all(db)
            logger.info("Marketplace tasks complete: %s", summary)
        except Exception:
            logger.exception("Marketplace tasks failed")
            await db.rollback()
            raise
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
