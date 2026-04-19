"""
Kaasb Platform - Admin Endpoints
All routes require admin/superuser access.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.core.database import get_db
from app.models.message import Conversation
from app.models.user import User
from app.schemas.admin import (
    AdminEscrowInfo,
    AdminJobListResponse,
    AdminJobStatusUpdate,
    AdminTransactionListResponse,
    AdminUserInfo,
    AdminUserListResponse,
    AdminUserStatusUpdate,
    PlatformStats,
)
from app.schemas.message import (
    ConversationJobInfo,
    ConversationListResponse,
    ConversationOrderInfo,
    ConversationSummary,
    MessageUserInfo,
)
from app.services.admin_service import AdminService
from app.services.message_service import MessageService

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
    role: str | None = Query(None, description="Filter: client|freelancer|admin"),
    status: str | None = Query(None, description="Filter: active|suspended|deactivated"),
    search: str | None = Query(None, description="Search by name/email/username"),
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
    status: str | None = Query(None, description="Filter: open|in_progress|completed|closed|cancelled"),
    search: str | None = Query(None),
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


# === Escrow Payout Management ===

@router.get(
    "/escrows",
    response_model=list[AdminEscrowInfo],
    summary="List funded escrows awaiting payout",
)
async def list_funded_escrows(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all FUNDED escrows with freelancer Qi Card details for manual payout."""
    service = AdminService(db)
    return await service.list_funded_escrows()


@router.post(
    "/escrows/{escrow_id}/release",
    summary="Mark escrow as released",
)
async def release_escrow(
    escrow_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Mark a funded escrow as released after sending the Qi Card payout manually."""
    service = AdminService(db)
    return await service.release_escrow_admin(escrow_id)


# === Transaction Overview ===

@router.get(
    "/transactions",
    response_model=AdminTransactionListResponse,
    summary="List all transactions",
)
async def list_transactions(
    type: str | None = Query(None, description="Filter: escrow_fund|escrow_release|platform_fee|payout"),
    status: str | None = Query(None, description="Filter: pending|completed|failed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all platform transactions."""
    service = AdminService(db)
    return await service.list_transactions_admin(type, status, page, page_size)


# === Support Inbox ===

def _serialize_support_conversation(c: Conversation) -> ConversationSummary:
    """
    Serialize a SUPPORT conversation for the admin inbox.
    The inbox is admin-centric: show the non-admin as "other_user" and report
    the ADMIN's unread count (messages from the user the admin hasn't seen).

    unread_one = messages sent by p2 that p1 hasn't read yet.
    unread_two = messages sent by p1 that p2 hasn't read yet.
    So "admin's unread" = unread_one when admin IS p1, unread_two when admin IS p2.
    """
    p1, p2 = c.participant_one, c.participant_two
    if p1.is_superuser and not p2.is_superuser:
        other = p2
        unread = c.unread_one  # admin is p1 → their pile is unread_one
    elif p2.is_superuser and not p1.is_superuser:
        other = p1
        unread = c.unread_two  # admin is p2 → their pile is unread_two
    else:
        # Fallback: neither or both are admins.
        other = p2 if c.unread_one >= c.unread_two else p1
        unread = max(c.unread_one, c.unread_two)

    return ConversationSummary(
        id=c.id,
        conversation_type=c.conversation_type,
        other_user=MessageUserInfo(
            id=other.id,
            username=other.username,
            first_name=other.first_name,
            last_name=other.last_name,
            avatar_url=other.avatar_url,
        ),
        job=ConversationJobInfo(id=c.job.id, title=c.job.title) if c.job else None,
        order=ConversationOrderInfo(id=c.order.id, status=c.order.status.value) if c.order else None,
        last_message_text=c.last_message_text,
        last_message_at=c.last_message_at,
        message_count=c.message_count,
        unread_count=unread,
        created_at=c.created_at,
    )


@router.get(
    "/support/conversations",
    response_model=ConversationListResponse,
    summary="List support conversations",
)
async def list_support_conversations(
    only_unread: bool = Query(False, description="Only threads with pending messages"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    List every SUPPORT conversation on the platform. Used by the admin
    support inbox to triage tickets across all admins — not scoped to the
    calling admin's own participant threads.
    """
    service = MessageService(db)
    result = await service.list_support_conversations(page, page_size, only_unread)
    conversations = [
        _serialize_support_conversation(c) for c in result["conversations"]
    ]
    return ConversationListResponse(
        conversations=conversations,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )
