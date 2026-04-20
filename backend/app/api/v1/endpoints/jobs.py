"""
Kaasb Platform - Job Endpoints
POST   /jobs                  - Create a new job (clients only)
GET    /jobs                  - Search/browse open jobs
GET    /jobs/my/posted        - Get current client's jobs
GET    /jobs/{job_id}         - Get job details
PUT    /jobs/{job_id}         - Update a job (owner only)
POST   /jobs/{job_id}/close   - Close a job (owner only)
DELETE /jobs/{job_id}         - Delete a job (owner only)
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_client
from app.core.database import get_db
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobDetail,
    JobListResponse,
    JobUpdate,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# === Public Endpoints ===


@router.get(
    "",
    response_model=JobListResponse,
    summary="Browse and search jobs",
)
async def search_jobs(
    q: str | None = Query(None, description="Search by title or description"),
    category: str | None = Query(None),
    job_type: str | None = Query(None, pattern=r"^fixed$"),
    skills: str | None = Query(
        None, description="Comma-separated skills filter"
    ),
    experience_level: str | None = Query(
        None, pattern=r"^(entry|intermediate|expert)$"
    ),
    budget_min: float | None = Query(None, ge=0),
    budget_max: float | None = Query(None, le=1000000),
    duration: str | None = Query(None),
    sort_by: str = Query(
        "newest",
        pattern=r"^(newest|oldest|budget_high|budget_low)$",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Browse and search open jobs with filters and sorting.

    - **q**: Text search in title and description
    - **category**: Filter by category
    - **job_type**: fixed (Kaasb is fixed-price only)
    - **skills**: Comma-separated list
    - **experience_level**: entry, intermediate, expert
    - **budget_min / budget_max**: Budget range
    - **duration**: Expected job duration
    - **sort_by**: newest, oldest, budget_high, budget_low
    """
    service = JobService(db)
    skills_list = [s.strip() for s in skills.split(",")] if skills else None

    return await service.search_jobs(
        query=q,
        category=category,
        job_type=job_type,
        skills=skills_list,
        experience_level=experience_level,
        budget_min=budget_min,
        budget_max=budget_max,
        duration=duration,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )


# === Authenticated Endpoints (Clients Only) ===
# NOTE: /my/posted MUST come before /{job_id} to avoid route conflict


@router.post(
    "",
    response_model=JobDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Post a new job",
)
async def create_job(
    data: JobCreate,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new job posting. Only clients can post jobs.

    Provide `fixed_price` (required) — Kaasb is fixed-price only.
    Optional `budget_min`/`budget_max` can be used to show a range in search.
    """
    service = JobService(db)
    return await service.create_job(current_user, data)


@router.get(
    "/my/posted",
    response_model=JobListResponse,
    summary="Get your posted jobs",
)
async def get_my_jobs(
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern=r"^(draft|open|in_progress|completed|cancelled|closed)$",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Get all jobs posted by the currently authenticated client."""
    service = JobService(db)
    return await service.get_client_jobs(
        client_id=current_user.id,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


# === Public detail (after /my/posted to avoid route conflict) ===


@router.get(
    "/{job_id}",
    response_model=JobDetail,
    summary="Get job details",
)
async def get_job(
    job_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a job posting."""
    service = JobService(db)
    job = await service.get_by_id(job_id)
    # Deduplicate view counts per IP+job to prevent manipulation
    client_ip = request.client.host if request.client else "unknown"
    await service.increment_view_deduplicated(job, client_ip)
    return job


@router.put(
    "/{job_id}",
    response_model=JobDetail,
    summary="Update a job posting",
)
async def update_job(
    job_id: uuid.UUID,
    data: JobUpdate,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a job posting. Only the job owner can edit.
    Only open or draft jobs can be edited.
    """
    service = JobService(db)
    return await service.update_job(job_id, current_user, data)


@router.post(
    "/{job_id}/close",
    response_model=JobDetail,
    summary="Close a job posting",
)
async def close_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """Close a job posting. Only the job owner can close it."""
    service = JobService(db)
    return await service.close_job(job_id, current_user)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a job posting",
)
async def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a job posting. Only the owner can delete.
    Only open/draft jobs with zero proposals can be deleted.
    """
    service = JobService(db)
    await service.delete_job(job_id, current_user)
    return {"detail": "Job deleted successfully"}
