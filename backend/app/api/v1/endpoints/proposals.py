"""
Kaasb Platform - Proposal Endpoints
POST   /proposals/jobs/{job_id}           - Submit a proposal (freelancer)
GET    /proposals/my                      - Get my proposals (freelancer)
GET    /proposals/jobs/{job_id}/list      - Get proposals on a job (client)
GET    /proposals/{proposal_id}           - Get proposal detail
PUT    /proposals/{proposal_id}           - Update proposal (freelancer)
POST   /proposals/{proposal_id}/withdraw  - Withdraw proposal (freelancer)
POST   /proposals/{proposal_id}/respond   - Respond to proposal (client)
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_client,
    get_current_freelancer,
    get_current_user,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.proposal import (
    ProposalCreate,
    ProposalDetail,
    ProposalListResponse,
    ProposalRespond,
    ProposalUpdate,
)
from app.services.proposal_service import ProposalService

router = APIRouter(prefix="/proposals", tags=["Proposals"])


# === Static / non-parameterized routes FIRST ===


@router.get(
    "/my",
    response_model=ProposalListResponse,
    summary="Get your submitted proposals",
)
async def get_my_proposals(
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern=r"^(pending|shortlisted|accepted|rejected|withdrawn)$",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_freelancer),
    db: AsyncSession = Depends(get_db),
):
    """Get all proposals submitted by the authenticated freelancer."""
    service = ProposalService(db)
    return await service.get_freelancer_proposals(
        freelancer=current_user,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


# === Routes with /jobs/{job_id} prefix ===


@router.post(
    "/jobs/{job_id}",
    response_model=ProposalDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a proposal on a job",
)
async def submit_proposal(
    job_id: uuid.UUID,
    data: ProposalCreate,
    current_user: User = Depends(get_current_freelancer),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a proposal on an open job. Freelancers only.
    One proposal per freelancer per job.
    """
    service = ProposalService(db)
    return await service.submit_proposal(current_user, job_id, data)


@router.get(
    "/jobs/{job_id}/list",
    response_model=ProposalListResponse,
    summary="Get proposals on your job",
)
async def get_job_proposals(
    job_id: uuid.UUID,
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern=r"^(pending|shortlisted|accepted|rejected|withdrawn)$",
    ),
    sort_by: str = Query(
        "newest",
        pattern=r"^(newest|oldest|bid_low|bid_high)$",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Get all proposals on a job. Client only, own jobs only."""
    service = ProposalService(db)
    return await service.get_job_proposals(
        client=current_user,
        job_id=job_id,
        status_filter=status_filter,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


# === Routes with /{proposal_id} parameter LAST ===


@router.get(
    "/{proposal_id}",
    response_model=ProposalDetail,
    summary="Get proposal details",
)
async def get_proposal(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get full proposal details.
    Visible to the freelancer who submitted it or the job's client.
    """
    service = ProposalService(db)
    return await service.get_proposal(current_user, proposal_id)


@router.put(
    "/{proposal_id}",
    response_model=ProposalDetail,
    summary="Update your proposal",
)
async def update_proposal(
    proposal_id: uuid.UUID,
    data: ProposalUpdate,
    current_user: User = Depends(get_current_freelancer),
    db: AsyncSession = Depends(get_db),
):
    """Update a pending proposal. Freelancer only, own proposals only."""
    service = ProposalService(db)
    return await service.update_proposal(current_user, proposal_id, data)


@router.post(
    "/{proposal_id}/withdraw",
    response_model=ProposalDetail,
    summary="Withdraw your proposal",
)
async def withdraw_proposal(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_freelancer),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw a pending or shortlisted proposal. Freelancer only."""
    service = ProposalService(db)
    return await service.withdraw_proposal(current_user, proposal_id)


@router.post(
    "/{proposal_id}/respond",
    response_model=ProposalDetail,
    summary="Respond to a proposal",
)
async def respond_to_proposal(
    proposal_id: uuid.UUID,
    data: ProposalRespond,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """
    Respond to a proposal: shortlist, accept, or reject.
    Client only, on proposals for own jobs.

    When a proposal is **accepted**:
    - The job status changes to 'in_progress'
    - The freelancer is assigned to the job
    - All other pending/shortlisted proposals are auto-rejected
    """
    service = ProposalService(db)
    return await service.respond_to_proposal(current_user, proposal_id, data)
