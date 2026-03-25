"""
Kaasb Platform - Admin Endpoints
All routes require admin/superuser access.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_admin
from app.models.user import User
from app.services.admin_service import AdminService
from app.schemas.admin import (
    PlatformStats,
    AdminUserListResponse,
    AdminUserInfo,
    AdminUserStatusUpdate,
    AdminJobListResponse,
    AdminJobStatusUpdate,
    AdminTransactionListResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


# === Platform Stats ===

@router.get(
    "/stats",
    response_model=PlatformStats,
    summary="Platform statistics",
)
async def get_platform_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive platform stats dashboard."""
    service = AdminService(db)
    return await service.get_platform_stats()


# === User Management ===

@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List all users",
)
async def list_users(
    role: Optional[str] = Query(None, description="Filter: client|freelancer|admin"),
    status: Optional[str] = Query(None, description="Filter: active|suspended|deactivated"),
    search: Optional[str] = Query(None, description="Search by name/email/username"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List users with filtering and search."""
    service = AdminService(db)
    return await service.list_users(role, status, search, page, page_size)


@router.put(
    "/users/{user_id}/status",
    response_model=AdminUserInfo,
    summary="Update user status",
)
async def update_user_status(
    user_id: uuid.UUID,
    data: AdminUserStatusUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Suspend, activate, or deactivate a user."""
    service = AdminService(db)
    return await service.update_user_status(user_id, data.status)


@router.post(
    "/users/{user_id}/toggle-admin",
    response_model=AdminUserInfo,
    summary="Toggle admin privileges",
)
async def toggle_admin(
    user_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Grant or revoke admin/superuser status."""
    service = AdminService(db)
    return await service.toggle_superuser(user_id, acting_admin=admin)


# === Job Moderation ===

@router.get(
    "/jobs",
    response_model=AdminJobListResponse,
    summary="List all jobs",
)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter: open|in_progress|completed|closed|cancelled"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all jobs for moderation."""
    service = AdminService(db)
    return await service.list_jobs_admin(status, search, page, page_size)


@router.put(
    "/jobs/{job_id}/status",
    summary="Update job status",
)
async def update_job_status(
    job_id: uuid.UUID,
    data: AdminJobStatusUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin updates job status (e.g., close a fraudulent listing)."""
    service = AdminService(db)
    job = await service.update_job_status(job_id, data.status)
    return {"id": str(job.id), "status": job.status.value, "message": f"Job status updated to {data.status}"}


# === Transaction Overview ===

@router.get(
    "/transactions",
    response_model=AdminTransactionListResponse,
    summary="List all transactions",
)
async def list_transactions(
    type: Optional[str] = Query(None, description="Filter: escrow_fund|escrow_release|platform_fee|payout"),
    status: Optional[str] = Query(None, description="Filter: pending|completed|failed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all platform transactions."""
    service = AdminService(db)
    return await service.list_transactions_admin(type, status, page, page_size)
