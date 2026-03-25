"""
Kaasb Platform - Proposal Service
Business logic for proposal submission, response, and listing.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.proposal import Proposal, ProposalStatus
from app.models.job import Job, JobStatus
from app.models.user import User
from app.schemas.proposal import ProposalCreate, ProposalUpdate, ProposalRespond

logger = logging.getLogger(__name__)


class ProposalService:
    """Service for proposal operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === Helpers ===

    async def _get_job(self, job_id: uuid.UUID) -> Job:
        """Get a job or 404."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )
        return job

    async def _get_proposal_with_relations(self, proposal_id: uuid.UUID) -> Proposal:
        """Get a proposal with freelancer and job loaded."""
        result = await self.db.execute(
            select(Proposal)
            .options(
                selectinload(Proposal.freelancer),
                selectinload(Proposal.job),
            )
            .where(Proposal.id == proposal_id)
        )
        proposal = result.scalar_one_or_none()
        if not proposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found",
            )
        return proposal

    # === Submit Proposal ===

    async def submit_proposal(
        self, freelancer: User, job_id: uuid.UUID, data: ProposalCreate
    ) -> Proposal:
        """Submit a proposal on a job (freelancer only)."""
        # Verify job exists and is open
        job = await self._get_job(job_id)

        if job.status != JobStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This job is no longer accepting proposals",
            )

        # Can't bid on own job
        if job.client_id == freelancer.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot submit a proposal on your own job",
            )

        # Check for existing proposal
        existing = await self.db.execute(
            select(Proposal).where(
                Proposal.job_id == job_id,
                Proposal.freelancer_id == freelancer.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already submitted a proposal for this job",
            )

        # Validate bid amount
        if data.bid_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bid amount must be greater than zero",
            )
        if job.budget_max and data.bid_amount > job.budget_max * 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bid amount exceeds reasonable range for this job (max budget: ${job.budget_max:.2f})",
            )

        # Create proposal
        proposal = Proposal(
            cover_letter=data.cover_letter,
            bid_amount=data.bid_amount,
            estimated_duration=data.estimated_duration,
            status=ProposalStatus.PENDING,
            job_id=job_id,
            freelancer_id=freelancer.id,
            submitted_at=datetime.now(timezone.utc),
        )

        self.db.add(proposal)

        # Atomically increment job's proposal count at the SQL level
        from sqlalchemy import update
        await self.db.execute(
            update(Job).where(Job.id == job_id).values(proposal_count=Job.proposal_count + 1)
        )

        await self.db.flush()
        await self.db.refresh(proposal, attribute_names=["freelancer", "job"])
        logger.info(f"Proposal submitted: {proposal.id} by freelancer={freelancer.id} on job={job_id}")
        return proposal

    # === Update Proposal (Freelancer) ===

    async def update_proposal(
        self, freelancer: User, proposal_id: uuid.UUID, data: ProposalUpdate
    ) -> Proposal:
        """Update a pending proposal (freelancer only)."""
        proposal = await self._get_proposal_with_relations(proposal_id)

        if proposal.freelancer_id != freelancer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own proposals",
            )

        if proposal.status != ProposalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit a proposal with status '{proposal.status.value}'",
            )

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        for field, value in update_data.items():
            setattr(proposal, field, value)

        await self.db.flush()
        await self.db.refresh(proposal, attribute_names=["freelancer", "job"])
        return proposal

    # === Withdraw Proposal (Freelancer) ===

    async def withdraw_proposal(
        self, freelancer: User, proposal_id: uuid.UUID
    ) -> Proposal:
        """Withdraw a pending/shortlisted proposal."""
        proposal = await self._get_proposal_with_relations(proposal_id)

        if proposal.freelancer_id != freelancer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only withdraw your own proposals",
            )

        if proposal.status not in (ProposalStatus.PENDING, ProposalStatus.SHORTLISTED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot withdraw a proposal with status '{proposal.status.value}'",
            )

        proposal.status = ProposalStatus.WITHDRAWN

        # Atomically decrement job's proposal count at the SQL level
        from sqlalchemy import update, case
        await self.db.execute(
            update(Job).where(Job.id == proposal.job_id).values(
                proposal_count=case(
                    (Job.proposal_count > 0, Job.proposal_count - 1),
                    else_=0,
                )
            )
        )

        await self.db.flush()
        await self.db.refresh(proposal, attribute_names=["freelancer", "job"])
        return proposal

    # === Respond to Proposal (Client) ===

    async def respond_to_proposal(
        self, client: User, proposal_id: uuid.UUID, data: ProposalRespond
    ) -> Proposal:
        """Client responds to a proposal (shortlist/accept/reject)."""
        proposal = await self._get_proposal_with_relations(proposal_id)

        # Verify the client owns the job
        if proposal.job.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only respond to proposals on your own jobs",
            )

        # Validate status transitions
        new_status = ProposalStatus(data.status)

        valid_transitions = {
            ProposalStatus.PENDING: {
                ProposalStatus.SHORTLISTED,
                ProposalStatus.ACCEPTED,
                ProposalStatus.REJECTED,
            },
            ProposalStatus.SHORTLISTED: {
                ProposalStatus.ACCEPTED,
                ProposalStatus.REJECTED,
            },
        }

        allowed = valid_transitions.get(proposal.status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change status from '{proposal.status.value}' to '{data.status}'",
            )

        proposal.status = new_status
        proposal.client_note = data.client_note
        proposal.responded_at = datetime.now(timezone.utc)

        # If accepted, update the job (with lock to prevent concurrent acceptance)
        if new_status == ProposalStatus.ACCEPTED:
            # Re-fetch job with FOR UPDATE lock to prevent race condition
            from sqlalchemy import update as sql_update
            job_result = await self.db.execute(
                select(Job).where(Job.id == proposal.job_id).with_for_update()
            )
            job = job_result.scalar_one_or_none()
            if not job or job.status != JobStatus.OPEN:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This job is no longer open — another proposal may have been accepted",
                )
            job.status = JobStatus.IN_PROGRESS
            job.freelancer_id = proposal.freelancer_id

            # Reject all other pending/shortlisted proposals
            other_proposals = await self.db.execute(
                select(Proposal).where(
                    Proposal.job_id == proposal.job_id,
                    Proposal.id != proposal.id,
                    Proposal.status.in_([
                        ProposalStatus.PENDING,
                        ProposalStatus.SHORTLISTED,
                    ]),
                )
            )
            for other in other_proposals.scalars().all():
                other.status = ProposalStatus.REJECTED
                other.client_note = "Another proposal was accepted for this job."
                other.responded_at = datetime.now(timezone.utc)

            # Auto-create contract
            from app.services.contract_service import ContractService
            contract_service = ContractService(self.db)
            await contract_service.create_contract_from_proposal(job, proposal)

        if new_status == ProposalStatus.ACCEPTED:
            logger.info(f"Proposal accepted: {proposal_id} by client={client.id}")
        elif new_status == ProposalStatus.REJECTED:
            logger.info(f"Proposal rejected: {proposal_id} by client={client.id}")

        await self.db.flush()
        await self.db.refresh(proposal, attribute_names=["freelancer", "job"])
        return proposal

    # === Get Single Proposal ===

    async def get_proposal(
        self, user: User, proposal_id: uuid.UUID
    ) -> Proposal:
        """Get a proposal — visible to the freelancer who submitted it or the job's client."""
        proposal = await self._get_proposal_with_relations(proposal_id)

        is_freelancer = proposal.freelancer_id == user.id
        is_client = proposal.job.client_id == user.id

        if not is_freelancer and not is_client:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this proposal",
            )

        return proposal

    # === List: Proposals on a Job (Client) ===

    async def get_job_proposals(
        self,
        client: User,
        job_id: uuid.UUID,
        status_filter: Optional[str] = None,
        sort_by: str = "newest",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all proposals on a job (client only)."""
        page_size = min(page_size, 100)
        # Verify client owns the job
        job = await self._get_job(job_id)
        if job.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view proposals on your own jobs",
            )

        stmt = (
            select(Proposal)
            .options(
                selectinload(Proposal.freelancer),
                selectinload(Proposal.job),
            )
            .where(Proposal.job_id == job_id)
        )

        if status_filter:
            stmt = stmt.where(Proposal.status == ProposalStatus(status_filter))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Sort
        if sort_by == "bid_low":
            stmt = stmt.order_by(Proposal.bid_amount.asc())
        elif sort_by == "bid_high":
            stmt = stmt.order_by(Proposal.bid_amount.desc())
        elif sort_by == "oldest":
            stmt = stmt.order_by(Proposal.submitted_at.asc())
        else:  # newest
            stmt = stmt.order_by(Proposal.submitted_at.desc())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        proposals = result.scalars().unique().all()

        return {
            "proposals": list(proposals),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    # === List: My Proposals (Freelancer) ===

    async def get_freelancer_proposals(
        self,
        freelancer: User,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all proposals submitted by the freelancer."""
        page_size = min(page_size, 100)
        stmt = (
            select(Proposal)
            .options(
                selectinload(Proposal.freelancer),
                selectinload(Proposal.job),
            )
            .where(Proposal.freelancer_id == freelancer.id)
        )

        if status_filter:
            stmt = stmt.where(Proposal.status == ProposalStatus(status_filter))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Order by newest first
        stmt = stmt.order_by(Proposal.submitted_at.desc())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        proposals = result.scalars().unique().all()

        return {
            "proposals": list(proposals),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
