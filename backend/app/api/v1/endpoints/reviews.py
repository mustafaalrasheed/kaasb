"""
Kaasb Platform - Review Endpoints
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.review import (
    ReviewCreate,
    ReviewDetail,
    ReviewListResponse,
    ReviewStats,
)
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews & Ratings"])


# === Static routes first ===

@router.get(
    "/user/{user_id}",
    response_model=ReviewListResponse,
    summary="Get reviews for a user",
)
async def get_user_reviews(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get public reviews received by a user. No auth required."""
    service = ReviewService(db)
    return await service.get_reviews_for_user(user_id, page, page_size)


@router.get(
    "/user/{user_id}/stats",
    response_model=ReviewStats,
    summary="Get review statistics for a user",
)
async def get_user_review_stats(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated review stats. No auth required."""
    service = ReviewService(db)
    return await service.get_review_stats(user_id)


@router.get(
    "/contract/{contract_id}",
    response_model=list[ReviewDetail],
    summary="Get reviews for a contract",
)
async def get_contract_reviews(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all reviews on a contract (both parties)."""
    service = ReviewService(db)
    return await service.get_contract_reviews(current_user, contract_id)


@router.post(
    "/contract/{contract_id}",
    response_model=ReviewDetail,
    summary="Submit a review",
    status_code=201,
)
async def submit_review(
    contract_id: uuid.UUID,
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a review for the other party on a completed contract."""
    service = ReviewService(db)
    return await service.submit_review(current_user, contract_id, data)
