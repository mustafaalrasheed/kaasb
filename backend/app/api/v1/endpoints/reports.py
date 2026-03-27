"""
Kaasb Platform - Content Moderation / Reporting Endpoints

POST /reports                       - Submit a content report
GET  /reports/my                    - List own submitted reports
GET  /reports/{id}                  - Get a specific report (reporter or admin)
GET  /reports                       - List all reports (admin only)
PUT  /reports/{id}/review           - Mark report reviewed with admin note (admin only)
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_current_user
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.report import Report, ReportReason, ReportStatus, ReportType
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Moderation"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReportCreate(BaseModel):
    report_type: ReportType
    target_id: uuid.UUID
    reason: ReportReason
    description: str | None = Field(None, max_length=1000)


class ReportReview(BaseModel):
    status: ReportStatus
    admin_note: str | None = Field(None, max_length=2000)


class ReportOut(BaseModel):
    id: uuid.UUID
    reporter_id: uuid.UUID
    report_type: ReportType
    target_id: uuid.UUID
    reason: ReportReason
    description: str | None
    status: ReportStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    admin_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# POST /reports — submit a report
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
    summary="Report content (job, user, message, review)",
)
async def submit_report(
    data: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a content moderation report.

    - **report_type**: `job`, `user`, `message`, or `review`
    - **target_id**: UUID of the reported resource
    - **reason**: Pre-defined category (spam, fraud, harassment, etc.)
    - **description**: Optional additional context (max 1 000 chars)
    """
    report = Report(
        reporter_id=current_user.id,
        report_type=data.report_type,
        target_id=data.target_id,
        reason=data.reason,
        description=data.description,
        status=ReportStatus.PENDING,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    logger.info(
        "Report submitted: type=%s target=%s by user=%s",
        data.report_type.value, data.target_id, current_user.id,
    )
    return report


# ---------------------------------------------------------------------------
# GET /reports/my — own reports
# ---------------------------------------------------------------------------

@router.get(
    "/my",
    response_model=ReportListResponse,
    summary="List your submitted reports",
)
async def list_my_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reports submitted by the authenticated user."""
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count(Report.id)).where(Report.reporter_id == current_user.id)
    )
    total = total_result.scalar() or 0

    reports_result = await db.execute(
        select(Report)
        .where(Report.reporter_id == current_user.id)
        .order_by(Report.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    reports = list(reports_result.scalars().all())

    return ReportListResponse(
        items=reports,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 1,
    )


# ---------------------------------------------------------------------------
# GET /reports/{id} — single report (reporter or admin)
# ---------------------------------------------------------------------------

@router.get(
    "/{report_id}",
    response_model=ReportOut,
    summary="Get a specific report",
)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a report by ID. Only the reporter or an admin may view it."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundError("Report", report_id)
    if report.reporter_id != current_user.id and not current_user.is_superuser:
        raise ForbiddenError("Access denied")
    return report


# ---------------------------------------------------------------------------
# GET /reports — admin list all reports
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=ReportListResponse,
    summary="List all reports (admin only)",
)
async def admin_list_reports(
    report_type: ReportType | None = Query(None),
    report_status: ReportStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all platform reports with optional filtering. Admin only."""
    offset = (page - 1) * page_size

    filters = []
    if report_type:
        filters.append(Report.report_type == report_type)
    if report_status:
        filters.append(Report.status == report_status)

    count_q = select(func.count(Report.id))
    list_q = select(Report).order_by(Report.created_at.desc()).offset(offset).limit(page_size)

    if filters:
        from sqlalchemy import and_
        combined = and_(*filters)
        count_q = count_q.where(combined)
        list_q = list_q.where(combined)

    total = (await db.execute(count_q)).scalar() or 0
    reports = list((await db.execute(list_q)).scalars().all())

    return ReportListResponse(
        items=reports,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total else 1,
    )


# ---------------------------------------------------------------------------
# PUT /reports/{id}/review — admin review
# ---------------------------------------------------------------------------

@router.put(
    "/{report_id}/review",
    response_model=ReportOut,
    summary="Review a report (admin only)",
)
async def review_report(
    report_id: uuid.UUID,
    data: ReportReview,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a report's status and add an admin note.
    Valid target statuses: `reviewed`, `resolved`, `dismissed`.
    """
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundError("Report", report_id)

    report.status = data.status
    report.admin_note = data.admin_note
    report.reviewed_by = admin.id
    report.reviewed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(report)

    logger.info(
        "Report %s reviewed by admin %s: status=%s",
        report_id, admin.id, data.status.value,
    )
    return report
