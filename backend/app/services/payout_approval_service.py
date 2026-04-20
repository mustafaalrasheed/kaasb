"""
Kaasb Platform - Payout Approval Service (Dual-Control)

Handles escrow releases that exceed the IQD threshold and therefore
need a second admin to approve before the money actually moves.

Flow:
  request_release(escrow_id, admin_A)
    - If escrow amount <= threshold: release immediately, log audit, done.
    - Else: create PayoutApproval(status=PENDING), log audit, return pending.
  approve(approval_id, admin_B)
    - Require admin_B != admin_A (four-eyes).
    - Release the underlying escrow, log audit, mark approval APPROVED.
  reject(approval_id, admin_B, note)
    - Require admin_B != admin_A.
    - Mark approval REJECTED, log audit. Escrow remains FUNDED; admin_A
      can either retry or refund.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.admin_audit import AdminAuditAction, PayoutApproval, PayoutApprovalStatus
from app.models.payment import Escrow, EscrowStatus
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)
settings = get_settings()


class PayoutApprovalService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    # ── Request release ──────────────────────────────────────────────────

    async def request_release(
        self,
        escrow_id: uuid.UUID,
        admin: User,
        *,
        note: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        """
        Admin clicks "Release" on a funded escrow. Either releases now
        (below threshold) or creates a pending approval (above threshold).
        """
        result = await self.db.execute(
            select(Escrow).where(
                Escrow.id == escrow_id,
                Escrow.status == EscrowStatus.FUNDED,
            ).with_for_update()
        )
        escrow = result.scalar_one_or_none()
        if not escrow:
            raise NotFoundError("Funded escrow")

        amount_iqd = float(escrow.amount)
        threshold = float(settings.PAYOUT_APPROVAL_THRESHOLD_IQD)

        # Below threshold — single admin, release immediately
        if amount_iqd <= threshold:
            release = await PaymentService(self.db).release_escrow_by_id(escrow_id)
            if not release:
                # Someone else released it between SELECT FOR UPDATE and now
                raise ConflictError("Escrow could not be released")

            await self.audit.log(
                admin_id=admin.id,
                action=AdminAuditAction.ESCROW_RELEASED,
                target_type="escrow",
                target_id=escrow_id,
                amount=amount_iqd,
                currency=escrow.currency,
                ip_address=ip_address,
                details={"mode": "single", "note": note},
            )
            await self.db.commit()
            return {
                "status": "released",
                "escrow_id": escrow_id,
                "amount": release.freelancer_amount,
                "currency": escrow.currency,
                "message": "Escrow released immediately (below dual-control threshold).",
            }

        # Above threshold — create approval request, NO money moves yet
        existing = await self.db.execute(
            select(PayoutApproval).where(
                PayoutApproval.escrow_id == escrow_id,
                PayoutApproval.status == PayoutApprovalStatus.PENDING,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError("An approval is already pending for this escrow")

        approval = PayoutApproval(
            escrow_id=escrow_id,
            requested_by_id=admin.id,
            amount=amount_iqd,
            currency=escrow.currency,
            status=PayoutApprovalStatus.PENDING,
            request_note=note,
        )
        self.db.add(approval)
        await self.db.flush()

        await self.audit.log(
            admin_id=admin.id,
            action=AdminAuditAction.ESCROW_RELEASE_REQUESTED,
            target_type="escrow",
            target_id=escrow_id,
            amount=amount_iqd,
            currency=escrow.currency,
            ip_address=ip_address,
            details={"approval_id": str(approval.id), "note": note, "threshold": threshold},
        )
        await self.db.commit()
        return {
            "status": "pending_second_approval",
            "escrow_id": escrow_id,
            "amount": amount_iqd,
            "currency": escrow.currency,
            "approval_id": approval.id,
            "message": (
                f"Amount {amount_iqd:,.0f} {escrow.currency} exceeds the dual-control "
                f"threshold ({threshold:,.0f} {escrow.currency}). A second admin must approve."
            ),
        }

    # ── Approve / reject ─────────────────────────────────────────────────

    async def approve(
        self,
        approval_id: uuid.UUID,
        admin: User,
        *,
        note: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        approval = await self._load_pending(approval_id)
        if approval.requested_by_id == admin.id:
            raise ForbiddenError(
                "The second approver must be a different admin than the requester."
            )

        # Release the underlying escrow
        release = await PaymentService(self.db).release_escrow_by_id(approval.escrow_id)
        if not release:
            # Escrow disappeared or state changed between request and approval.
            # Mark the approval cancelled so it leaves the queue.
            approval.status = PayoutApprovalStatus.CANCELLED
            approval.decided_by_id = admin.id
            approval.decided_at = datetime.now(UTC)
            approval.decision_note = "Cancelled — escrow no longer in FUNDED state."
            await self.db.commit()
            raise ConflictError("Escrow is no longer available for release.")

        approval.status = PayoutApprovalStatus.APPROVED
        approval.decided_by_id = admin.id
        approval.decided_at = datetime.now(UTC)
        approval.decision_note = note

        await self.audit.log(
            admin_id=admin.id,
            action=AdminAuditAction.PAYOUT_APPROVED,
            target_type="payout_approval",
            target_id=approval.id,
            amount=float(approval.amount),
            currency=approval.currency,
            ip_address=ip_address,
            details={
                "escrow_id": str(approval.escrow_id),
                "requested_by": str(approval.requested_by_id),
                "note": note,
            },
        )
        await self.audit.log(
            admin_id=admin.id,
            action=AdminAuditAction.ESCROW_RELEASED,
            target_type="escrow",
            target_id=approval.escrow_id,
            amount=float(approval.amount),
            currency=approval.currency,
            ip_address=ip_address,
            details={"mode": "dual-control", "approval_id": str(approval.id)},
        )
        await self.db.commit()
        return {
            "status": "released",
            "approval_id": approval.id,
            "escrow_id": approval.escrow_id,
            "amount": release.freelancer_amount,
            "currency": approval.currency,
        }

    async def reject(
        self,
        approval_id: uuid.UUID,
        admin: User,
        *,
        note: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        approval = await self._load_pending(approval_id)
        if approval.requested_by_id == admin.id:
            raise ForbiddenError(
                "The rejecter must be a different admin than the requester."
            )
        if not note or len(note.strip()) < 3:
            raise BadRequestError("A rejection reason is required (min 3 chars).")

        approval.status = PayoutApprovalStatus.REJECTED
        approval.decided_by_id = admin.id
        approval.decided_at = datetime.now(UTC)
        approval.decision_note = note.strip()

        await self.audit.log(
            admin_id=admin.id,
            action=AdminAuditAction.PAYOUT_REJECTED,
            target_type="payout_approval",
            target_id=approval.id,
            amount=float(approval.amount),
            currency=approval.currency,
            ip_address=ip_address,
            details={
                "escrow_id": str(approval.escrow_id),
                "requested_by": str(approval.requested_by_id),
                "reason": note,
            },
        )
        await self.db.commit()
        return {
            "status": "rejected",
            "approval_id": approval.id,
            "escrow_id": approval.escrow_id,
        }

    # ── Queries ──────────────────────────────────────────────────────────

    async def list_pending(self) -> list[dict]:
        result = await self.db.execute(
            select(PayoutApproval)
            .where(PayoutApproval.status == PayoutApprovalStatus.PENDING)
            .order_by(PayoutApproval.created_at.asc())
        )
        approvals = list(result.scalars().all())
        if not approvals:
            return []

        # Gather context for the admin reviewer: requester email, escrow → freelancer + order
        requester_ids = {a.requested_by_id for a in approvals if a.requested_by_id}
        escrow_ids = [a.escrow_id for a in approvals]

        requesters: dict[uuid.UUID, User] = {}
        if requester_ids:
            r = await self.db.execute(select(User).where(User.id.in_(requester_ids)))
            requesters = {u.id: u for u in r.scalars().all()}

        e = await self.db.execute(select(Escrow).where(Escrow.id.in_(escrow_ids)))
        escrows = {es.id: es for es in e.scalars().all()}

        freelancer_ids = {es.freelancer_id for es in escrows.values() if es.freelancer_id}
        freelancers: dict[uuid.UUID, User] = {}
        if freelancer_ids:
            f = await self.db.execute(select(User).where(User.id.in_(freelancer_ids)))
            freelancers = {u.id: u for u in f.scalars().all()}

        rows = []
        for a in approvals:
            es = escrows.get(a.escrow_id)
            fl = freelancers.get(es.freelancer_id) if es else None
            req = requesters.get(a.requested_by_id) if a.requested_by_id else None
            rows.append({
                "id": a.id,
                "escrow_id": a.escrow_id,
                "amount": float(a.amount),
                "currency": a.currency,
                "status": a.status.value,
                "requested_by_id": a.requested_by_id,
                "requested_by_email": req.email if req else None,
                "decided_by_id": a.decided_by_id,
                "decided_by_email": None,
                "request_note": a.request_note,
                "decision_note": a.decision_note,
                "decided_at": a.decided_at,
                "created_at": a.created_at,
                "freelancer_id": es.freelancer_id if es else None,
                "freelancer_email": fl.email if fl else None,
                "freelancer_username": fl.username if fl else None,
                "gig_order_id": es.gig_order_id if es else None,
                "milestone_id": es.milestone_id if es else None,
            })
        return rows

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _load_pending(self, approval_id: uuid.UUID) -> PayoutApproval:
        result = await self.db.execute(
            select(PayoutApproval)
            .where(PayoutApproval.id == approval_id)
            .with_for_update()
        )
        approval = result.scalar_one_or_none()
        if not approval:
            raise NotFoundError("Payout approval")
        if approval.status != PayoutApprovalStatus.PENDING:
            raise ConflictError(f"Approval already {approval.status.value}.")
        return approval

    @staticmethod
    async def count_pending(db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(PayoutApproval.id)).where(
                PayoutApproval.status == PayoutApprovalStatus.PENDING
            )
        )
        return int(result.scalar_one() or 0)
