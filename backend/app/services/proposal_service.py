"""
Kaasb Platform - Proposal Service
Business logic for proposal submission, response, and listing.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.job import Job, JobStatus
from app.models.notification import NotificationType
from app.models.proposal import Proposal, ProposalStatus
from app.models.user import User
from app.schemas.proposal import ProposalCreate, ProposalRespond, ProposalUpdate
from app.services.base import BaseService
from app.services.notification_service import notify

logger = logging.getLogger(__name__)


class ProposalService(BaseService):
    """Service for proposal operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    # === Helpers ===

    async def _get_job(self, job_id: uuid.UUID) -> Job:
        """Get a job or 404."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("Job")
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
            raise NotFoundError("Proposal")
        return proposal

    # === Submit Proposal ===

    async def submit_proposal(
        self, freelancer: User, job_id: uuid.UUID, data: ProposalCreate
    ) -> Proposal:
        """Submit a proposal on a job (freelancer only)."""
        # Verify job exists and is open
        job = await self._get_job(job_id)

        if job.status != JobStatus.OPEN:
            raise BadRequestError("This job is no longer accepting proposals")

        # Can't bid on own job
        if job.client_id == freelancer.id:
            raise BadRequestError("You cannot submit a proposal on your own job")

        # Check for existing proposal
        existing = await self.db.execute(
            select(Proposal).where(
                Proposal.job_id == job_id,
                Proposal.freelancer_id == freelancer.id,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("You have already submitted a proposal for this job")

        # Validate bid amount
        if data.bid_amount <= 0:
            raise BadRequestError("Bid amount must be greater than zero")
        if job.budget_max and data.bid_amount > job.budget_max * 2:
            raise BadRequestError(
                f"Bid amount exceeds reasonable range for this job (max budget: ${job.budget_max:.2f})"
            )

        # Create proposal
        proposal = Proposal(
            cover_letter=data.cover_letter,
            bid_amount=data.bid_amount,
            estimated_duration=data.estimated_duration,
            status=ProposalStatus.PENDING,
            job_id=job_id,
            freelancer_id=freelancer.id,
            submitted_at=datetime.now(UTC),
        )

        self.db.add(proposal)

        # Atomically increment job's proposal count at the SQL level
        await self.db.execute(
            update(Job).where(Job.id == job_id).values(proposal_count=Job.proposal_count + 1)
        )

        await self.db.flush()
        await self.db.refresh(proposal, attribute_names=["freelancer", "job"])
        logger.info("Proposal submitted: %s by freelancer=%s on job=%s", proposal.id, freelancer.id, job_id)

        # Notify the client about the new proposal
        freelancer_name = f"{freelancer.first_name} {freelancer.last_name}"
        await notify(
            self.db,
            user_id=job.client_id,
            type=NotificationType.PROPOSAL_RECEIVED,
            title_ar="عرض جديد على وظيفتك",
            title_en="New proposal on your job",
            message_ar=f"قدّم {freelancer_name} عرضاً على وظيفة: {job.title}",
            message_en=f"{freelancer_name} submitted a proposal on: {job.title}",
            link_type="job",
            link_id=job_id,
            actor_id=freelancer.id,
        )

        return proposal

    # === Update Proposal (Freelancer) ===

    async def update_proposal(
        self, freelancer: User, proposal_id: uuid.UUID, data: ProposalUpdate
    ) -> Proposal:
        """Update a pending proposal (freelancer only)."""
        proposal = await self._get_proposal_with_relations(proposal_id)

        if proposal.freelancer_id != freelancer.id:
            raise ForbiddenError("You can only edit your own proposals")

        if proposal.status != ProposalStatus.PENDING:
            raise BadRequestError(f"Cannot edit a proposal with status '{proposal.status.value}'")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise BadRequestError("No fields to update")

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
            raise ForbiddenError("You can only withdraw your own proposals")

        if proposal.status not in (ProposalStatus.PENDING, ProposalStatus.SHORTLISTED):
            raise BadRequestError(f"Cannot withdraw a proposal with status '{proposal.status.value}'")

        proposal.status = ProposalStatus.WITHDRAWN

        # Atomically decrement job's proposal count at the SQL level
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
            raise ForbiddenError("You can only respond to proposals on your own jobs")

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
            raise BadRequestError(f"Cannot change status from '{proposal.status.value}' to '{data.status}'")

        proposal.status = new_status
        proposal.client_note = data.client_note
        proposal.responded_at = datetime.now(UTC)

        # If accepted, update the job (with lock to prevent concurrent acceptance)
        if new_status == ProposalStatus.ACCEPTED:
            # Re-fetch job with FOR UPDATE lock to prevent race condition
            job_result = await self.db.execute(
                select(Job).where(Job.id == proposal.job_id).with_for_update()
            )
            job = job_result.scalar_one_or_none()
            if not job or job.status != JobStatus.OPEN:
                raise ConflictError("This job is no longer open — another proposal may have been accepted")
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
                other.responded_at = datetime.now(UTC)

            # Auto-create contract
            from app.services.contract_service import ContractService
            contract_service = ContractService(self.db)
            await contract_service.create_contract_from_proposal(job, proposal)

            # Auto-create the working-relationship chat so both parties land
            # directly in a ready thread after acceptance. Bypasses the
            # initiation gate — acceptance IS the authorization event.
            from app.services.message_service import MessageService
            msg_service = MessageService(self.db)
            await msg_service.get_or_create_system_conversation(
                client_id=client.id,
                freelancer_id=proposal.freelancer_id,
                job_id=proposal.job_id,
                system_message=(
                    f"تم قبول العرض — يمكنكما الآن التنسيق هنا بخصوص: {job.title}\n"
                    f"Proposal accepted — you can now coordinate here about: {job.title}"
                ),
            )

        if new_status == ProposalStatus.ACCEPTED:
            logger.info("Proposal accepted: %s by client=%s", proposal_id, client.id)
        elif new_status == ProposalStatus.REJECTED:
            logger.info("Proposal rejected: %s by client=%s", proposal_id, client.id)

        await self.db.flush()
        await self.db.refresh(proposal, attribute_names=["freelancer", "job"])

        # Notify the freelancer of the decision
        job_title = proposal.job.title if proposal.job else ""
        if new_status == ProposalStatus.ACCEPTED:
            await notify(
                self.db,
                user_id=proposal.freelancer_id,
                type=NotificationType.PROPOSAL_ACCEPTED,
                title_ar="تم قبول عرضك",
                title_en="Your proposal was accepted",
                message_ar=f"تهانينا! قبل العميل عرضك على وظيفة: {job_title}",
                message_en=f"Congrats — the client accepted your proposal on: {job_title}",
                link_type="job",
                link_id=proposal.job_id,
                actor_id=client.id,
            )
        elif new_status == ProposalStatus.REJECTED:
            await notify(
                self.db,
                user_id=proposal.freelancer_id,
                type=NotificationType.PROPOSAL_REJECTED,
                title_ar="تم رفض عرضك",
                title_en="Your proposal was declined",
                message_ar=f"للأسف، رفض العميل عرضك على وظيفة: {job_title}",
                message_en=f"The client declined your proposal on: {job_title}",
                link_type="job",
                link_id=proposal.job_id,
                actor_id=client.id,
            )
        elif new_status == ProposalStatus.SHORTLISTED:
            await notify(
                self.db,
                user_id=proposal.freelancer_id,
                type=NotificationType.PROPOSAL_SHORTLISTED,
                title_ar="عرضك في القائمة المختصرة",
                title_en="You've been shortlisted",
                message_ar=f"أضاف العميل عرضك إلى القائمة المختصرة لوظيفة: {job_title}",
                message_en=f"The client shortlisted your proposal on: {job_title}",
                link_type="job",
                link_id=proposal.job_id,
                actor_id=client.id,
            )

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
            raise ForbiddenError("You do not have access to this proposal")

        return proposal

    # === List: Proposals on a Job (Client) ===

    async def get_job_proposals(
        self,
        client: User,
        job_id: uuid.UUID,
        status_filter: str | None = None,
        sort_by: str = "newest",
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all proposals on a job (client only)."""
        page_size = self.clamp_page_size(page_size)
        # Verify client owns the job
        job = await self._get_job(job_id)
        if job.client_id != client.id:
            raise ForbiddenError("You can only view proposals on your own jobs")

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

        return self.paginated_response(items=list(proposals), total=total, page=page, page_size=page_size, key="proposals")

    # === List: My Proposals (Freelancer) ===

    async def get_freelancer_proposals(
        self,
        freelancer: User,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all proposals submitted by the freelancer."""
        page_size = self.clamp_page_size(page_size)
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

        return self.paginated_response(items=list(proposals), total=total, page=page, page_size=page_size, key="proposals")
