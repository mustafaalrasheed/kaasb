"""
Kaasb Platform - Contract Endpoints
"""

from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_user, get_current_client, get_current_freelancer
from app.models.user import User
from app.services.contract_service import ContractService
from app.schemas.contract import (
    ContractDetail,
    ContractListResponse,
    ContractCreate,
    ContractUserInfo,
    ContractJobInfo,
    MilestoneDetail,
    MilestoneUpdate,
    MilestoneSubmit,
    MilestoneReview,
)

router = APIRouter(prefix="/contracts", tags=["Contracts & Milestones"])


# === Helper: serialize contract summary with milestone counts ===

def _serialize_summary(c) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "total_amount": c.total_amount,
        "amount_paid": c.amount_paid,
        "status": c.status.value,
        "started_at": c.started_at,
        "client": ContractUserInfo.model_validate(c.client).model_dump(),
        "freelancer": ContractUserInfo.model_validate(c.freelancer).model_dump(),
        "job": ContractJobInfo.model_validate(c.job).model_dump(),
        "milestone_count": getattr(c, "_milestone_count", len(c.milestones)),
        "completed_milestones": getattr(c, "_completed_milestones", 0),
    }


# === Static routes first ===

@router.get(
    "/my",
    response_model=ContractListResponse,
    summary="List my contracts",
)
async def get_my_contracts(
    status: Optional[str] = Query(None, description="Filter: active|completed|cancelled|disputed|paused"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all contracts where you are either the client or the freelancer."""
    service = ContractService(db)
    result = await service.get_my_contracts(
        user=current_user,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
    return {
        "contracts": [_serialize_summary(c) for c in result["contracts"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


# === Parameterized routes ===

@router.get(
    "/{contract_id}",
    response_model=ContractDetail,
    summary="Get contract detail",
)
async def get_contract(
    contract_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full contract details with all milestones."""
    service = ContractService(db)
    contract = await service.get_contract(current_user, contract_id)
    return contract


@router.post(
    "/{contract_id}/milestones",
    response_model=ContractDetail,
    summary="Add milestones to contract",
    status_code=201,
)
async def add_milestones(
    contract_id: uuid.UUID,
    data: ContractCreate,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Client adds milestones to a contract. Total must not exceed contract amount."""
    service = ContractService(db)
    contract = await service.add_milestones(current_user, contract_id, data)
    return contract


@router.put(
    "/milestones/{milestone_id}",
    response_model=MilestoneDetail,
    summary="Update a pending milestone",
)
async def update_milestone(
    milestone_id: uuid.UUID,
    data: MilestoneUpdate,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Client edits a pending milestone's title, description, amount, or due date."""
    service = ContractService(db)
    milestone = await service.update_milestone(current_user, milestone_id, data)
    return milestone


@router.delete(
    "/milestones/{milestone_id}",
    status_code=204,
    summary="Delete a pending milestone",
)
async def delete_milestone(
    milestone_id: uuid.UUID,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Client deletes a pending milestone."""
    service = ContractService(db)
    await service.delete_milestone(current_user, milestone_id)


@router.post(
    "/milestones/{milestone_id}/start",
    response_model=MilestoneDetail,
    summary="Start working on milestone",
)
async def start_milestone(
    milestone_id: uuid.UUID,
    current_user: User = Depends(get_current_freelancer),
    db: AsyncSession = Depends(get_db),
):
    """Freelancer marks a pending milestone as in-progress."""
    service = ContractService(db)
    milestone = await service.start_milestone(current_user, milestone_id)
    return milestone


@router.post(
    "/milestones/{milestone_id}/submit",
    response_model=MilestoneDetail,
    summary="Submit milestone for review",
)
async def submit_milestone(
    milestone_id: uuid.UUID,
    data: MilestoneSubmit,
    current_user: User = Depends(get_current_freelancer),
    db: AsyncSession = Depends(get_db),
):
    """Freelancer submits a milestone for client review."""
    service = ContractService(db)
    milestone = await service.submit_milestone(current_user, milestone_id, data)
    return milestone


@router.post(
    "/milestones/{milestone_id}/review",
    response_model=MilestoneDetail,
    summary="Review submitted milestone",
)
async def review_milestone(
    milestone_id: uuid.UUID,
    data: MilestoneReview,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Client approves a submitted milestone or requests revision."""
    service = ContractService(db)
    milestone = await service.review_milestone(current_user, milestone_id, data)
    return milestone
