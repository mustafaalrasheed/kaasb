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
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.admin_audit import AdminAuditAction, AdminAuditLog, PayoutApproval, PayoutApprovalStatus
from app.models.payment import Escrow, EscrowStatus
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)
settings = get_settings()

# Rolling window used when deciding whether to trigger dual-control based on
# cumulative payouts to a freelancer. Catches the "split a large release into
# several below-threshold releases" bypass flagged in nightly-2026-04-25 P0 #2.
# 24h is long enough to catch a deliberate split, short enough that a naturally
# high-volume freelancer's legitimate weekly earnings don't keep hitting dual
# control indefinitely.
_FREELANCER_AGGREGATION_WINDOW = timedelta(hours=24)


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

        # Aggregation-based threshold check (nightly-2026-04-25 P0 #2):
        # the naive per-escrow check allowed an admin to split a single
        # logical payout into N sub-threshold escrows for the same
        # freelancer and release them all without a second signature. Sum
        # up (a) recent releases in the last 24h to the same freelancer +
        # (b) any pending approvals queued for the same freelancer +
        # (c) this release's amount. If the total crosses the threshold,
        # dual-control kicks in regardless of individual row size.
        freelancer_total = await self._freelancer_recent_release_total(
            escrow.freelancer_id
        )
        aggregate = freelancer_total + amount_iqd
        requires_dual = amount_iqd > threshold or aggregate > threshold

        # Below threshold AND cumulative under-threshold — release immediately
        if not requires_dual:
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
            details={
                "approval_id": str(approval.id),
                "note": note,
                "threshold": threshold,
                "freelancer_24h_total": freelancer_total,
                "aggregate_including_this": aggregate,
            },
        )
        await self.db.commit()
        # Choose the wording based on WHY dual control triggered so the
        # requesting admin understands whether it was this escrow alone or
        # a cumulative rule — helps distinguish legitimate big payouts
        # from "I was splitting on purpose and got caught".
        if amount_iqd > threshold:
            message = (
                f"Amount {amount_iqd:,.0f} {escrow.currency} exceeds the dual-control "
                f"threshold ({threshold:,.0f} {escrow.currency}). A second admin must approve."
            )
        else:
            message = (
                f"Releases to this freelancer in the last 24h total "
                f"{aggregate:,.0f} {escrow.currency} (with this one), which exceeds the "
                f"dual-control threshold ({threshold:,.0f} {escrow.currency}). "
                f"A second admin must approve."
            )
        return {
            "status": "pending_second_approval",
            "escrow_id": escrow_id,
            "amount": amount_iqd,
            "currency": escrow.currency,
            "approval_id": approval.id,
            "message": message,
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
                "service_order_id": es.service_order_id if es else None,
                "milestone_id": es.milestone_id if es else None,
            })
        return rows

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _freelancer_recent_release_total(
        self, freelancer_id: uuid.UUID
    ) -> float:
        """Total IQD released (or queued to release) to ``freelancer_id`` in the
        rolling aggregation window, from ANY admin. Two sums added together:

        1. Audited ``ESCROW_RELEASED`` actions targeting that freelancer's
           escrows within the last ``_FREELANCER_AGGREGATION_WINDOW``.
        2. Currently PENDING ``PayoutApproval`` rows for that freelancer,
           regardless of age — if they get approved they add to today's
           outbound, so they have to count now.

        Filtering by ANY admin (not just the caller) ensures the rule
        survives a two-admin collusion where each stays under threshold by
        splitting escrows between them.
        """
        cutoff = datetime.now(UTC) - _FREELANCER_AGGREGATION_WINDOW

        released_q = await self.db.execute(
            select(func.coalesce(func.sum(AdminAuditLog.amount), 0.0))
            .select_from(AdminAuditLog)
            .join(Escrow, Escrow.id == AdminAuditLog.target_id)
            .where(
                AdminAuditLog.action == AdminAuditAction.ESCROW_RELEASED,
                AdminAuditLog.target_type == "escrow",
                AdminAuditLog.created_at >= cutoff,
                Escrow.freelancer_id == freelancer_id,
            )
        )
        released_sum = float(released_q.scalar_one() or 0.0)

        pending_q = await self.db.execute(
            select(func.coalesce(func.sum(PayoutApproval.amount), 0.0))
            .select_from(PayoutApproval)
            .join(Escrow, Escrow.id == PayoutApproval.escrow_id)
            .where(
                PayoutApproval.status == PayoutApprovalStatus.PENDING,
                Escrow.freelancer_id == freelancer_id,
            )
        )
        pending_sum = float(pending_q.scalar_one() or 0.0)

        return released_sum + pending_sum

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
