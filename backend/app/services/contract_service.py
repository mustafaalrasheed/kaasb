"""
Kaasb Platform - Contract Service
Business logic for contracts and milestone management.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.contract import (
    Contract, ContractStatus,
    Milestone, MilestoneStatus,
)
from app.models.job import Job, JobStatus
from app.models.proposal import Proposal
from app.models.user import User
from app.schemas.contract import (
    ContractCreate, MilestoneCreate, MilestoneUpdate,
    MilestoneSubmit, MilestoneReview,
)


class ContractService:
    """Service for contract and milestone operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === Helpers ===

    async def _get_contract(self, contract_id: uuid.UUID) -> Contract:
        """Get a contract with all relations loaded."""
        result = await self.db.execute(
            select(Contract)
            .options(
                selectinload(Contract.client),
                selectinload(Contract.freelancer),
                selectinload(Contract.job),
                selectinload(Contract.milestones),
            )
            .where(Contract.id == contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contract not found",
            )
        return contract

    async def _get_milestone(self, milestone_id: uuid.UUID) -> Milestone:
        """Get a milestone with contract loaded."""
        result = await self.db.execute(
            select(Milestone)
            .options(selectinload(Milestone.contract))
            .where(Milestone.id == milestone_id)
        )
        milestone = result.scalar_one_or_none()
        if not milestone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Milestone not found",
            )
        return milestone

    def _check_contract_access(self, contract: Contract, user: User) -> str:
        """Check user has access and return their role on this contract."""
        if user.id == contract.client_id:
            return "client"
        if user.id == contract.freelancer_id:
            return "freelancer"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this contract",
        )

    # === Create Contract (called from proposal acceptance) ===

    async def create_contract_from_proposal(
        self, job: Job, proposal: Proposal
    ) -> Contract:
        """Auto-create a contract when a proposal is accepted."""
        contract = Contract(
            title=job.title,
            description=job.description,
            total_amount=proposal.bid_amount,
            amount_paid=0.0,
            status=ContractStatus.ACTIVE,
            job_id=job.id,
            proposal_id=proposal.id,
            client_id=job.client_id,
            freelancer_id=proposal.freelancer_id,
            started_at=datetime.now(timezone.utc),
            deadline=job.deadline,
        )
        self.db.add(contract)
        await self.db.flush()
        return contract

    # === Add Milestones (Client) ===

    async def add_milestones(
        self, client: User, contract_id: uuid.UUID, data: ContractCreate
    ) -> Contract:
        """Client adds milestones to a contract."""
        contract = await self._get_contract(contract_id)

        if contract.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the client can add milestones",
            )

        if contract.status != ContractStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only add milestones to active contracts",
            )

        # Validate total doesn't exceed contract amount
        existing_total = sum(m.amount for m in contract.milestones)
        new_total = sum(m.amount for m in data.milestones)

        if existing_total + new_total > contract.total_amount * 1.01:  # 1% tolerance
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Milestone total (${existing_total + new_total:.2f}) "
                       f"exceeds contract amount (${contract.total_amount:.2f})",
            )

        # Determine order start
        max_order = max((m.order for m in contract.milestones), default=-1)

        for i, m_data in enumerate(data.milestones):
            milestone = Milestone(
                title=m_data.title,
                description=m_data.description,
                amount=m_data.amount,
                order=m_data.order if m_data.order > 0 else max_order + 1 + i,
                due_date=m_data.due_date,
                status=MilestoneStatus.PENDING,
                contract_id=contract.id,
            )
            self.db.add(milestone)

        await self.db.flush()

        # Expire the contract so the identity map doesn't serve the cached
        # empty milestones collection — force a fresh DB fetch
        self.db.expire(contract)

        # Reload
        return await self._get_contract(contract_id)

    # === Update Milestone (Client) ===

    async def update_milestone(
        self, client: User, milestone_id: uuid.UUID, data: MilestoneUpdate
    ) -> Milestone:
        """Client updates a pending milestone."""
        milestone = await self._get_milestone(milestone_id)
        contract = milestone.contract

        if contract.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the client can update milestones",
            )

        if milestone.status != MilestoneStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only edit pending milestones",
            )

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        for field, value in update_data.items():
            setattr(milestone, field, value)

        await self.db.flush()
        await self.db.refresh(milestone)
        return milestone

    # === Delete Milestone (Client) ===

    async def delete_milestone(
        self, client: User, milestone_id: uuid.UUID
    ) -> None:
        """Client deletes a pending milestone."""
        milestone = await self._get_milestone(milestone_id)
        contract = milestone.contract

        if contract.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the client can delete milestones",
            )

        if milestone.status != MilestoneStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only delete pending milestones",
            )

        await self.db.delete(milestone)
        await self.db.flush()

    # === Start Milestone (Freelancer) ===

    async def start_milestone(
        self, freelancer: User, milestone_id: uuid.UUID
    ) -> Milestone:
        """Freelancer starts working on a milestone."""
        milestone = await self._get_milestone(milestone_id)
        contract = milestone.contract

        if contract.freelancer_id != freelancer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned freelancer can start milestones",
            )

        if milestone.status != MilestoneStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start a milestone with status '{milestone.status.value}'",
            )

        milestone.status = MilestoneStatus.IN_PROGRESS
        await self.db.flush()
        await self.db.refresh(milestone)
        return milestone

    # === Submit Milestone (Freelancer) ===

    async def submit_milestone(
        self, freelancer: User, milestone_id: uuid.UUID, data: MilestoneSubmit
    ) -> Milestone:
        """Freelancer submits a milestone for client review."""
        milestone = await self._get_milestone(milestone_id)
        contract = milestone.contract

        if contract.freelancer_id != freelancer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the assigned freelancer can submit milestones",
            )

        allowed = {MilestoneStatus.IN_PROGRESS, MilestoneStatus.REVISION_REQUESTED}
        if milestone.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit a milestone with status '{milestone.status.value}'",
            )

        milestone.status = MilestoneStatus.SUBMITTED
        milestone.submitted_at = datetime.now(timezone.utc)
        milestone.submission_note = data.submission_note
        milestone.feedback = None  # Clear previous feedback

        await self.db.flush()
        await self.db.refresh(milestone)
        return milestone

    # === Review Milestone (Client) ===

    async def review_milestone(
        self, client: User, milestone_id: uuid.UUID, data: MilestoneReview
    ) -> Milestone:
        """Client reviews a submitted milestone — approve or request revision."""
        milestone = await self._get_milestone(milestone_id)
        contract = milestone.contract

        if contract.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the client can review milestones",
            )

        if milestone.status != MilestoneStatus.SUBMITTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only review submitted milestones",
            )

        milestone.feedback = data.feedback

        if data.action == "approve":
            milestone.status = MilestoneStatus.APPROVED
            milestone.approved_at = datetime.now(timezone.utc)

            # Auto-mark as paid (in real system, payment would happen first)
            milestone.status = MilestoneStatus.PAID
            milestone.paid_at = datetime.now(timezone.utc)

            # Update contract amount_paid
            full_contract = await self._get_contract(contract.id)
            full_contract.amount_paid = sum(
                m.amount for m in full_contract.milestones
                if m.status == MilestoneStatus.PAID
            )

            # Check if all milestones are paid → complete contract
            all_paid = all(
                m.status == MilestoneStatus.PAID
                for m in full_contract.milestones
            )
            if all_paid and len(full_contract.milestones) > 0:
                full_contract.status = ContractStatus.COMPLETED
                full_contract.completed_at = datetime.now(timezone.utc)

                # Update job status
                job_result = await self.db.execute(
                    select(Job).where(Job.id == full_contract.job_id)
                )
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = JobStatus.COMPLETED

                # Update user stats
                full_contract.freelancer.total_earnings += milestone.amount
                full_contract.freelancer.jobs_completed += 1
                full_contract.client.total_spent += milestone.amount
            else:
                # Just update client spent for this milestone
                full_contract.client.total_spent += milestone.amount
                full_contract.freelancer.total_earnings += milestone.amount

        elif data.action == "request_revision":
            milestone.status = MilestoneStatus.REVISION_REQUESTED

        await self.db.flush()
        await self.db.refresh(milestone)
        return milestone

    # === Get Contract Detail ===

    async def get_contract(
        self, user: User, contract_id: uuid.UUID
    ) -> Contract:
        """Get contract detail — accessible by client or freelancer."""
        contract = await self._get_contract(contract_id)
        self._check_contract_access(contract, user)
        # Sort milestones by order
        contract.milestones.sort(key=lambda m: m.order)
        return contract

    # === List My Contracts ===

    async def get_my_contracts(
        self,
        user: User,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all contracts for the current user (as client or freelancer)."""
        stmt = (
            select(Contract)
            .options(
                selectinload(Contract.client),
                selectinload(Contract.freelancer),
                selectinload(Contract.job),
                selectinload(Contract.milestones),
            )
            .where(
                (Contract.client_id == user.id) | (Contract.freelancer_id == user.id)
            )
        )

        if status_filter:
            stmt = stmt.where(Contract.status == ContractStatus(status_filter))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Order by newest
        stmt = stmt.order_by(Contract.started_at.desc())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        contracts = result.scalars().unique().all()

        # Enrich with milestone counts
        enriched = []
        for c in contracts:
            c._milestone_count = len(c.milestones)
            c._completed_milestones = sum(
                1 for m in c.milestones if m.status == MilestoneStatus.PAID
            )
            enriched.append(c)

        return {
            "contracts": enriched,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
