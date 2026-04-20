"""
Kaasb Platform - Admin Endpoints
All routes require admin/superuser access.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_current_staff
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.middleware.security import _get_client_ip
from app.models.admin_audit import AdminAuditAction, AdminAuditLog
from app.models.message import Conversation
from app.models.user import User
from app.schemas.admin import (
    AdminAuditLogInfo,
    AdminAuditLogListResponse,
    AdminEscrowInfo,
    AdminJobListResponse,
    AdminJobStatusUpdate,
    AdminTransactionListResponse,
    AdminUserInfo,
    AdminUserListResponse,
    AdminUserStatusUpdate,
    PayoutApprovalDecision,
    PayoutApprovalInfo,
    PayoutApprovalListResponse,
    PlatformStats,
    ReleaseRequestBody,
    ReleaseRequestResult,
)
from app.schemas.message import (
    ConversationJobInfo,
    ConversationListResponse,
    ConversationOrderInfo,
    ConversationSummary,
    MessageListResponse,
    MessageUserInfo,
)
from app.services.admin_service import AdminService
from app.services.audit_service import AuditService
from app.services.message_service import MessageService
from app.services.payout_approval_service import PayoutApprovalService

router = APIRouter(prefix="/admin", tags=["Admin"])


# === Platform Stats ===

@router.get(
    "/stats",
    response_model=PlatformStats,
    summary="Platform statistics",
)
async def get_platform_stats(
    _staff: User = Depends(get_current_staff),
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
    _staff: User = Depends(get_current_staff),
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
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Suspend, activate, or deactivate a user."""
    service = AdminService(db)
    user = await service.update_user_status(user_id, data.status)
    await AuditService(db).log(
        admin_id=admin.id,
        action=AdminAuditAction.USER_STATUS_CHANGED,
        target_type="user",
        target_id=user_id,
        ip_address=_get_client_ip(request),
        details={"new_status": data.status, "target_email": user.email},
    )
    await db.commit()
    return user


@router.post(
    "/users/{user_id}/toggle-admin",
    response_model=AdminUserInfo,
    summary="Toggle admin privileges",
)
async def toggle_admin(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Grant or revoke admin/superuser status."""
    service = AdminService(db)
    user = await service.toggle_superuser(user_id, acting_admin=admin)
    await AuditService(db).log(
        admin_id=admin.id,
        action=(
            AdminAuditAction.USER_PROMOTED_ADMIN
            if user.is_superuser
            else AdminAuditAction.USER_DEMOTED_ADMIN
        ),
        target_type="user",
        target_id=user_id,
        ip_address=_get_client_ip(request),
        details={"target_email": user.email},
    )
    await db.commit()
    return user


@router.post(
    "/users/{user_id}/toggle-support",
    response_model=AdminUserInfo,
    summary="Toggle support role",
)
async def toggle_support(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Grant or revoke limited-privilege support role. Support staff can triage
    disputes and handle support chat but cannot release funds or change user
    state — those remain gated on is_superuser.
    """
    service = AdminService(db)
    user = await service.toggle_support(user_id, acting_admin=admin)
    await AuditService(db).log(
        admin_id=admin.id,
        action=(
            AdminAuditAction.USER_PROMOTED_SUPPORT
            if user.is_support
            else AdminAuditAction.USER_DEMOTED_SUPPORT
        ),
        target_type="user",
        target_id=user_id,
        ip_address=_get_client_ip(request),
        details={"target_email": user.email},
    )
    await db.commit()
    return user


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
    _staff: User = Depends(get_current_staff),
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
    _staff: User = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all FUNDED escrows with freelancer Qi Card details for manual payout."""
    service = AdminService(db)
    return await service.list_funded_escrows()


@router.post(
    "/escrows/{escrow_id}/release",
    response_model=ReleaseRequestResult,
    summary="Request escrow release (dual-control above threshold)",
)
async def release_escrow(
    escrow_id: uuid.UUID,
    request: Request,
    body: ReleaseRequestBody | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Request release of a FUNDED escrow.

    - Amount ≤ PAYOUT_APPROVAL_THRESHOLD_IQD: released immediately.
    - Amount > threshold: creates a pending PayoutApproval. A different admin
      must call /admin/payout-approvals/{id}/approve before money moves.
    """
    service = PayoutApprovalService(db)
    return await service.request_release(
        escrow_id,
        admin,
        note=(body.note if body else None),
        ip_address=_get_client_ip(request),
    )


# === Dual-Control Payout Approvals ===

@router.get(
    "/payout-approvals/pending",
    response_model=PayoutApprovalListResponse,
    summary="List pending payout approvals",
)
async def list_pending_payout_approvals(
    _staff: User = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all PayoutApprovals awaiting a second admin's decision."""
    service = PayoutApprovalService(db)
    rows = await service.list_pending()
    return PayoutApprovalListResponse(
        approvals=[PayoutApprovalInfo(**r) for r in rows],
        total=len(rows),
    )


@router.post(
    "/payout-approvals/{approval_id}/approve",
    summary="Approve a pending payout (second admin)",
)
async def approve_payout_approval(
    approval_id: uuid.UUID,
    request: Request,
    body: PayoutApprovalDecision | None = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Second admin approves a pending payout. Must differ from the requester.
    On approval, the underlying escrow is released immediately.
    """
    service = PayoutApprovalService(db)
    return await service.approve(
        approval_id,
        admin,
        note=(body.note if body else None),
        ip_address=_get_client_ip(request),
    )


@router.post(
    "/payout-approvals/{approval_id}/reject",
    summary="Reject a pending payout (second admin)",
)
async def reject_payout_approval(
    approval_id: uuid.UUID,
    body: PayoutApprovalDecision,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Second admin rejects a pending payout with a reason. The escrow stays
    FUNDED so the requester can retry or refund.
    """
    service = PayoutApprovalService(db)
    return await service.reject(
        approval_id,
        admin,
        note=body.note,
        ip_address=_get_client_ip(request),
    )


# === Admin Audit Log ===

@router.get(
    "/audit-logs",
    response_model=AdminAuditLogListResponse,
    summary="List admin audit log entries",
)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _staff: User = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """Paginated admin action audit log, newest first."""
    from sqlalchemy import select

    service = AuditService(db)
    rows, total = await service.list_recent(
        limit=page_size, offset=(page - 1) * page_size
    )

    admin_ids = {r.admin_id for r in rows if r.admin_id}
    admins: dict[uuid.UUID, User] = {}
    if admin_ids:
        res = await db.execute(select(User).where(User.id.in_(admin_ids)))
        admins = {u.id: u for u in res.scalars().all()}

    def _serialize(r: AdminAuditLog) -> AdminAuditLogInfo:
        a = admins.get(r.admin_id) if r.admin_id else None
        return AdminAuditLogInfo(
            id=r.id,
            admin_id=r.admin_id,
            admin_email=a.email if a else None,
            action=r.action.value,
            target_type=r.target_type,
            target_id=r.target_id,
            amount=float(r.amount) if r.amount is not None else None,
            currency=r.currency,
            ip_address=r.ip_address,
            details=r.details,
            created_at=r.created_at,
        )

    return AdminAuditLogListResponse(
        logs=[_serialize(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


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
    _staff: User = Depends(get_current_staff),
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
    _staff: User = Depends(get_current_staff),
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


@router.get(
    "/orders/{order_id}/conversation",
    response_model=MessageListResponse,
    summary="Get order conversation for dispute review",
)
async def get_order_conversation(
    order_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    staff: User = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Staff: fetch the client-freelancer chat for a given order.
    Used when reviewing disputes to see full conversation history.
    Staff presence does NOT mark messages as read or emit read receipts.
    """
    service = MessageService(db)
    conv = await service.get_order_conversation(order_id)
    if not conv:
        raise NotFoundError("Order conversation")
    return await service.get_messages(staff, conv.id, page, page_size)
