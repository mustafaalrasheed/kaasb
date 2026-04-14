"""
Kaasb Platform - Review Service
Business logic for reviews and rating aggregation.
"""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.contract import Contract, ContractStatus
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class ReviewService(BaseService):
    """Service for review operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def submit_review(
        self, reviewer: User, contract_id: uuid.UUID, data: ReviewCreate
    ) -> Review:
        """Submit a review for the other party on a completed contract."""
        result = await self.db.execute(
            select(Contract)
            .options(
                selectinload(Contract.client),
                selectinload(Contract.freelancer),
            )
            .where(Contract.id == contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            raise NotFoundError("Contract")

        if contract.status != ContractStatus.COMPLETED:
            raise BadRequestError("Can only review completed contracts")

        if reviewer.id == contract.client_id:
            reviewee_id = contract.freelancer_id
        elif reviewer.id == contract.freelancer_id:
            reviewee_id = contract.client_id
        else:
            raise ForbiddenError("You are not part of this contract")

        existing = await self.db.execute(
            select(Review).where(
                Review.contract_id == contract_id,
                Review.reviewer_id == reviewer.id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("You have already reviewed this contract")

        review = Review(
            rating=data.rating,
            comment=data.comment,
            communication_rating=data.communication_rating,
            quality_rating=data.quality_rating,
            professionalism_rating=data.professionalism_rating,
            timeliness_rating=data.timeliness_rating,
            contract_id=contract_id,
            reviewer_id=reviewer.id,
            reviewee_id=reviewee_id,
        )
        self.db.add(review)
        await self.db.flush()

        await self._update_user_rating(reviewee_id)

        await self.db.refresh(review, attribute_names=["reviewer", "reviewee", "contract"])
        logger.info("Review submitted: %s by reviewer=%s on contract=%s", review.id, reviewer.id, contract_id)
        return review

    async def _update_user_rating(self, user_id: uuid.UUID):
        """Recalculate user's average rating and total reviews."""
        result = await self.db.execute(
            select(
                func.avg(Review.rating),
                func.count(Review.id),
            ).where(Review.reviewee_id == user_id)
        )
        row = result.one()
        avg_rating = float(row[0]) if row[0] else 0.0
        total_reviews = row[1] or 0

        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            user.avg_rating = round(avg_rating, 2)
            user.total_reviews = total_reviews
            await self.db.flush()

    async def get_reviews_for_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all reviews received by a user."""
        page_size = self.clamp_page_size(page_size)
        stmt = (
            select(Review)
            .options(
                selectinload(Review.reviewer),
                selectinload(Review.reviewee),
                selectinload(Review.contract),
            )
            .where(Review.reviewee_id == user_id, Review.is_public.is_(True))
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        avg_result = await self.db.execute(
            select(func.avg(Review.rating)).where(
                Review.reviewee_id == user_id, Review.is_public.is_(True)
            )
        )
        avg_rating = avg_result.scalar()

        stmt = stmt.order_by(Review.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        reviews = result.scalars().unique().all()

        result_dict = self.paginated_response(items=list(reviews), total=total, page=page, page_size=page_size, key="reviews")
        result_dict["average_rating"] = round(float(avg_rating), 2) if avg_rating else None
        return result_dict

    async def get_review_stats(self, user_id: uuid.UUID) -> dict:
        """Get aggregated review statistics."""
        stats_result = await self.db.execute(
            select(
                func.avg(Review.rating),
                func.count(Review.id),
                func.avg(Review.communication_rating),
                func.avg(Review.quality_rating),
                func.avg(Review.professionalism_rating),
                func.avg(Review.timeliness_rating),
            ).where(Review.reviewee_id == user_id, Review.is_public.is_(True))
        )
        row = stats_result.one()

        dist_result = await self.db.execute(
            select(Review.rating, func.count(Review.id))
            .where(Review.reviewee_id == user_id, Review.is_public.is_(True))
            .group_by(Review.rating)
        )
        distribution = {str(i): 0 for i in range(1, 6)}
        for rating, count in dist_result.all():
            distribution[str(rating)] = count

        return {
            "average_rating": round(float(row[0]), 2) if row[0] else 0.0,
            "total_reviews": row[1] or 0,
            "rating_distribution": distribution,
            "avg_communication": round(float(row[2]), 2) if row[2] else None,
            "avg_quality": round(float(row[3]), 2) if row[3] else None,
            "avg_professionalism": round(float(row[4]), 2) if row[4] else None,
            "avg_timeliness": round(float(row[5]), 2) if row[5] else None,
        }

    async def get_contract_reviews(
        self, user: User, contract_id: uuid.UUID
    ) -> list[Review]:
        """Get reviews for a specific contract (both parties)."""
        result = await self.db.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            raise NotFoundError("Contract")

        if user.id not in (contract.client_id, contract.freelancer_id):
            raise ForbiddenError("Not part of this contract")

        result = await self.db.execute(
            select(Review)
            .options(
                selectinload(Review.reviewer),
                selectinload(Review.reviewee),
                selectinload(Review.contract),
            )
            .where(Review.contract_id == contract_id)
        )
        return list(result.scalars().unique().all())
