"""
Kaasb Platform - Job Service
Business logic for job posting, listing, search, and lifecycle management.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.job import Job, JobStatus, JobType, ExperienceLevel, JobDuration
from app.models.user import User, UserRole
from app.schemas.job import JobCreate, JobUpdate

logger = logging.getLogger(__name__)


class JobService:
    """Service for job posting operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === Create ===

    async def create_job(self, client: User, data: JobCreate) -> Job:
        """Create a new job posting."""
        if client.primary_role != UserRole.CLIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only clients can post jobs",
            )

        job = Job(
            title=data.title,
            description=data.description,
            category=data.category,
            job_type=JobType(data.job_type),
            budget_min=data.budget_min,
            budget_max=data.budget_max,
            fixed_price=data.fixed_price,
            skills_required=data.skills_required,
            experience_level=(
                ExperienceLevel(data.experience_level)
                if data.experience_level
                else None
            ),
            duration=(
                JobDuration(data.duration) if data.duration else None
            ),
            deadline=data.deadline,
            client_id=client.id,
            status=JobStatus.OPEN,
            published_at=datetime.now(timezone.utc),
        )

        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job, attribute_names=["client"])
        logger.info(f"Job created: {job.id} by client={client.id}")
        return job

    # === Read ===

    async def get_by_id(self, job_id: uuid.UUID) -> Job:
        """Get a single job by ID with client info."""
        result = await self.db.execute(
            select(Job)
            .options(selectinload(Job.client))
            .where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )
        return job

    async def increment_view(self, job: Job) -> None:
        """Increment the view count for a job."""
        job.view_count += 1
        await self.db.flush()

    # === Update ===

    async def update_job(
        self, job_id: uuid.UUID, client: User, data: JobUpdate
    ) -> Job:
        """Update an existing job posting (owner only, while open/draft)."""
        job = await self.get_by_id(job_id)

        if job.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own jobs",
            )

        if job.status not in (JobStatus.OPEN, JobStatus.DRAFT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit a job with status '{job.status.value}'",
            )

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        # Map string enums back to enum types
        if "job_type" in update_data:
            update_data["job_type"] = JobType(update_data["job_type"])
        if "experience_level" in update_data and update_data["experience_level"]:
            update_data["experience_level"] = ExperienceLevel(
                update_data["experience_level"]
            )
        if "duration" in update_data and update_data["duration"]:
            update_data["duration"] = JobDuration(update_data["duration"])

        for field, value in update_data.items():
            setattr(job, field, value)

        await self.db.flush()
        await self.db.refresh(job, attribute_names=["client"])
        logger.info(f"Job updated: {job.id} by client={client.id}")
        return job

    # === Status Changes ===

    async def close_job(self, job_id: uuid.UUID, client: User) -> Job:
        """Close a job posting (owner only)."""
        job = await self.get_by_id(job_id)

        if job.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only close your own jobs",
            )

        if job.status not in (JobStatus.OPEN, JobStatus.DRAFT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot close a job with status '{job.status.value}'",
            )

        job.status = JobStatus.CLOSED
        job.closed_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(job, attribute_names=["client"])
        logger.info(f"Job closed: {job.id} by client={client.id}")
        return job

    async def delete_job(self, job_id: uuid.UUID, client: User) -> None:
        """Delete a job posting (owner only, draft/open with no proposals)."""
        job = await self.get_by_id(job_id)

        if job.client_id != client.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own jobs",
            )

        if job.status not in (JobStatus.OPEN, JobStatus.DRAFT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only delete open or draft jobs",
            )

        if job.proposal_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a job that has proposals. Close it instead.",
            )

        await self.db.delete(job)
        await self.db.flush()
        logger.info(f"Job deleted: {job_id} by client={client.id}")

    # === Search & Listing ===

    async def search_jobs(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        job_type: Optional[str] = None,
        skills: Optional[list[str]] = None,
        experience_level: Optional[str] = None,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        duration: Optional[str] = None,
        sort_by: str = "newest",  # newest, oldest, budget_high, budget_low
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search open jobs with filters, sorting, and pagination."""
        page_size = min(page_size, 100)
        stmt = (
            select(Job)
            .options(selectinload(Job.client))
            .where(Job.status == JobStatus.OPEN)
        )

        # Text search on title and description (limit length to prevent abuse)
        if query:
            query = query[:200]
            search_term = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Job.title.ilike(search_term),
                    Job.description.ilike(search_term),
                )
            )

        # Category filter
        if category:
            category = category[:100]
            stmt = stmt.where(Job.category.ilike(f"%{category}%"))

        # Job type filter
        if job_type:
            stmt = stmt.where(Job.job_type == JobType(job_type))

        # Skills filter (ANY match)
        if skills:
            stmt = stmt.where(Job.skills_required.overlap(skills))

        # Experience level filter
        if experience_level:
            stmt = stmt.where(
                Job.experience_level == ExperienceLevel(experience_level)
            )

        # Budget range filter
        if budget_min is not None:
            stmt = stmt.where(
                or_(
                    Job.fixed_price >= budget_min,
                    Job.budget_min >= budget_min,
                )
            )
        if budget_max is not None:
            stmt = stmt.where(
                or_(
                    Job.fixed_price <= budget_max,
                    Job.budget_max <= budget_max,
                )
            )

        # Duration filter
        if duration:
            stmt = stmt.where(Job.duration == JobDuration(duration))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sorting
        if sort_by == "oldest":
            stmt = stmt.order_by(Job.published_at.asc())
        elif sort_by == "budget_high":
            stmt = stmt.order_by(
                func.coalesce(Job.fixed_price, Job.budget_max, 0).desc()
            )
        elif sort_by == "budget_low":
            stmt = stmt.order_by(
                func.coalesce(Job.fixed_price, Job.budget_min, 0).asc()
            )
        else:  # newest (default)
            stmt = stmt.order_by(Job.published_at.desc().nullslast())

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        jobs = result.scalars().unique().all()

        return {
            "jobs": list(jobs),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def get_client_jobs(
        self,
        client_id: uuid.UUID,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all jobs posted by a specific client."""
        page_size = min(page_size, 100)
        stmt = (
            select(Job)
            .options(selectinload(Job.client))
            .where(Job.client_id == client_id)
        )

        if status_filter:
            stmt = stmt.where(Job.status == JobStatus(status_filter))

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Order and paginate
        stmt = stmt.order_by(Job.created_at.desc())
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        jobs = result.scalars().unique().all()

        return {
            "jobs": list(jobs),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
