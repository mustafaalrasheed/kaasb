"""
Kaasb Platform - Job Service
Business logic for job posting, listing, search, and lifecycle management.
"""

import hashlib
import logging
import time
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import ExperienceLevel, Job, JobDuration, JobStatus, JobType
from app.models.user import User, UserRole
from app.schemas.job import JobCreate, JobUpdate
from app.services.base import BaseService
from app.utils.sanitize import escape_like

logger = logging.getLogger(__name__)

# Simple in-memory dedup cache for view counts (IP+job_id -> last_view_time)
# Prevents bots from inflating views. TTL: 1 hour per unique viewer.
_VIEW_DEDUP_CACHE: dict[str, float] = {}
_VIEW_DEDUP_TTL = 3600  # 1 hour
_VIEW_DEDUP_MAX_KEYS = 50_000


class JobService(BaseService):
    """Service for job posting operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

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
            published_at=datetime.now(UTC),
        )

        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job, attribute_names=["client"])
        logger.info("Job created: %s by client=%s", job.id, client.id)
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
        """Atomically increment the view count for a job at the SQL level."""
        await self.db.execute(
            update(Job).where(Job.id == job.id).values(view_count=Job.view_count + 1)
        )
        await self.db.flush()

    async def increment_view_deduplicated(self, job: Job, client_ip: str) -> None:
        """Increment view count only once per IP per job per hour."""
        global _VIEW_DEDUP_CACHE
        now = time.time()

        # Create a short hash key for privacy and memory efficiency
        raw_key = f"{client_ip}:{job.id}"
        dedup_key = hashlib.md5(raw_key.encode()).hexdigest()[:16]

        last_view = _VIEW_DEDUP_CACHE.get(dedup_key)
        if last_view and (now - last_view) < _VIEW_DEDUP_TTL:
            return  # Already viewed recently, skip

        # Evict old entries if cache is too large
        if len(_VIEW_DEDUP_CACHE) > _VIEW_DEDUP_MAX_KEYS:
            expired = [k for k, v in _VIEW_DEDUP_CACHE.items() if now - v >= _VIEW_DEDUP_TTL]
            for k in expired:
                del _VIEW_DEDUP_CACHE[k]

        _VIEW_DEDUP_CACHE[dedup_key] = now
        await self.increment_view(job)

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
        logger.info("Job updated: %s by client=%s", job.id, client.id)
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
        job.closed_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(job, attribute_names=["client"])
        logger.info("Job closed: %s by client=%s", job.id, client.id)
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
        logger.info("Job deleted: %s by client=%s", job_id, client.id)

    # === Search & Listing ===

    async def search_jobs(
        self,
        query: str | None = None,
        category: str | None = None,
        job_type: str | None = None,
        skills: list[str] | None = None,
        experience_level: str | None = None,
        budget_min: float | None = None,
        budget_max: float | None = None,
        duration: str | None = None,
        sort_by: str = "newest",  # newest, oldest, budget_high, budget_low
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search open jobs with filters, sorting, and pagination."""
        page_size = self.clamp_page_size(page_size)

        # Build filter conditions once — reuse for both COUNT and SELECT
        # This avoids the subquery overhead of wrapping the full SELECT in a COUNT
        filters = [Job.status == JobStatus.OPEN]

        if query:
            search_term = f"%{escape_like(query[:200])}%"
            filters.append(
                or_(
                    Job.title.ilike(search_term),
                    Job.description.ilike(search_term),
                )
            )
        if category:
            filters.append(Job.category.ilike(f"%{escape_like(category[:100])}%"))
        if job_type:
            filters.append(Job.job_type == JobType(job_type))
        if skills:
            filters.append(Job.skills_required.overlap(skills))
        if experience_level:
            filters.append(Job.experience_level == ExperienceLevel(experience_level))
        if budget_min is not None:
            filters.append(or_(Job.fixed_price >= budget_min, Job.budget_min >= budget_min))
        if budget_max is not None:
            filters.append(or_(Job.fixed_price <= budget_max, Job.budget_max <= budget_max))
        if duration:
            filters.append(Job.duration == JobDuration(duration))

        # COUNT query — direct WHERE avoids subquery overhead (~2x faster)
        total = (await self.db.execute(
            select(func.count(Job.id)).where(*filters)
        )).scalar() or 0

        # DATA query with eager loading and sorting
        stmt = select(Job).options(selectinload(Job.client)).where(*filters)

        if sort_by == "oldest":
            stmt = stmt.order_by(Job.published_at.asc())
        elif sort_by == "budget_high":
            stmt = stmt.order_by(func.coalesce(Job.fixed_price, Job.budget_max, 0).desc())
        elif sort_by == "budget_low":
            stmt = stmt.order_by(func.coalesce(Job.fixed_price, Job.budget_min, 0).asc())
        else:  # newest (default) — uses ix_jobs_status_published index
            stmt = stmt.order_by(Job.published_at.desc().nullslast())

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        jobs = result.scalars().unique().all()

        return self.paginated_response(items=list(jobs), total=total, page=page, page_size=page_size, key="jobs")

    async def get_client_jobs(
        self,
        client_id: uuid.UUID,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get all jobs posted by a specific client."""
        page_size = self.clamp_page_size(page_size)

        # Build filters once for reuse in COUNT and SELECT
        filters = [Job.client_id == client_id]
        if status_filter:
            filters.append(Job.status == JobStatus(status_filter))

        # Direct COUNT — no subquery needed
        total = (await self.db.execute(
            select(func.count(Job.id)).where(*filters)
        )).scalar() or 0

        # Data query — uses ix_jobs_client_created index
        stmt = (
            select(Job)
            .options(selectinload(Job.client))
            .where(*filters)
            .order_by(Job.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(stmt)
        jobs = result.scalars().unique().all()

        return self.paginated_response(items=list(jobs), total=total, page=page, page_size=page_size, key="jobs")
