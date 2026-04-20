"""
Kaasb Platform - Dispute Service (F5)
Dedicated dispute lifecycle: create, assign, resolve.
Works alongside existing GigOrder.dispute_* fields.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.dispute import Dispute, DisputeStatus
from app.models.gig import GigOrder, GigOrderStatus
from app.models.notification import NotificationType
from app.models.payment import Escrow, EscrowStatus
from app.models.user import User, UserStatus
from app.schemas.dispute import DisputeCreate
from app.services.base import BaseService
from app.services.notification_service import notify_background


class DisputeService(BaseService):
    """Service for F5 Dispute model lifecycle."""

    async def open_dispute(
        self,
        order_id: uuid.UUID,
        initiator: User,
        data: DisputeCreate,
    ) -> Dispute:
        """
        Open a formal Dispute record for an order.
        Also updates GigOrder status to DISPUTED and freezes escrow
        (delegates to existing GigService logic where applicable).
        """
        order = await self.db.get(GigOrder, order_id)
        if not order:
            raise NotFoundError("Order")

        # Only order participants can open a dispute
        is_client = str(order.client_id) == str(initiator.id)
        is_freelancer = str(order.freelancer_id) == str(initiator.id)
        if not is_client and not is_freelancer:
            raise ForbiddenError("Only order participants can raise a dispute")

        # Check order is in a disputable state
        allowed = {
            GigOrderStatus.IN_PROGRESS,
            GigOrderStatus.DELIVERED,
            GigOrderStatus.REVISION_REQUESTED,
            GigOrderStatus.PENDING_REQUIREMENTS,
        }
        if order.status not in allowed:
            raise BadRequestError(
                f"Cannot open a dispute on an order with status '{order.status.value}'"
            )

        # Only one dispute per order
        existing = await self.db.execute(
            select(Dispute).where(Dispute.order_id == order_id)
        )
        if existing.scalar_one_or_none():
            raise ConflictError("A dispute already exists for this order")

        initiated_by = "client" if is_client else "freelancer"

        dispute = Dispute(
            order_id=order_id,
            initiated_by=initiated_by,
            reason=data.reason,
            description=data.description,
            evidence_files=data.evidence_files,
            status=DisputeStatus.OPEN,
        )
        self.db.add(dispute)

        # Update order status and freeze escrow
        order.status = GigOrderStatus.DISPUTED
        order.dispute_opened_at = datetime.now(UTC)
        order.dispute_opened_by = initiator.id
        order.dispute_reason = data.description[:500]

        escrow_result = await self.db.execute(
            select(Escrow).where(
                Escrow.gig_order_id == order_id,
                Escrow.status == EscrowStatus.FUNDED,
            )
        )
        escrow = escrow_result.scalar_one_or_none()
        if escrow:
            escrow.status = EscrowStatus.DISPUTED

        await self.db.commit()
        await self.db.refresh(dispute)

        # Notify the other party
        notify_target = order.freelancer_id if is_client else order.client_id
        asyncio.create_task(notify_background(
            user_id=notify_target,
            type=NotificationType.DISPUTE_OPENED,
            title="تم فتح نزاع على طلبك",
            message=f"السبب: {data.description[:200]}",
            link_type="gig_order",
            link_id=str(order_id),
            actor_id=initiator.id,
        ))

        # Notify admins
        admin_result = await self.db.execute(
            select(User).where(
                User.is_superuser == True,  # noqa: E712
                User.status == UserStatus.ACTIVE,
            )
        )
        for admin in admin_result.scalars().all():
            asyncio.create_task(notify_background(
                user_id=admin.id,
                type=NotificationType.DISPUTE_OPENED,
                title="نزاع جديد يحتاج مراجعة",
                message=f"طلب #{str(order_id)[:8]} — {data.reason.value}: {data.description[:150]}",
                link_type="gig_order",
                link_id=str(order_id),
                actor_id=initiator.id,
            ))

        return await self._load_dispute_by_id(dispute.id)  # type: ignore[return-value]

    async def get_dispute_by_order(self, order_id: uuid.UUID, user: User) -> Dispute:
        order = await self.db.get(GigOrder, order_id)
        if not order:
            raise NotFoundError("Order")
        is_participant = str(user.id) in (str(order.client_id), str(order.freelancer_id))
        if not is_participant and not user.is_superuser:
            raise ForbiddenError("Access denied")

        dispute = await self.db.execute(
            select(Dispute)
            .where(Dispute.order_id == order_id)
            .options(selectinload(Dispute.admin))
        )
        result = dispute.scalar_one_or_none()
        if not result:
            raise NotFoundError("Dispute")
        return result

    async def assign_admin(
        self, dispute_id: uuid.UUID, admin: User, notes: str | None = None
    ) -> Dispute:
        """Admin takes ownership of a dispute."""
        dispute = await self.db.get(Dispute, dispute_id)
        if not dispute:
            raise NotFoundError("Dispute")
        if dispute.status not in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW):
            raise BadRequestError(f"Cannot assign to dispute with status '{dispute.status.value}'")
        dispute.admin_id = admin.id
        dispute.status = DisputeStatus.UNDER_REVIEW
        if notes:
            dispute.admin_notes = notes
        await self.db.commit()
        return await self._load_dispute_by_id(dispute.id)  # type: ignore[return-value]

    async def resolve_dispute(
        self,
        dispute_id: uuid.UUID,
        admin: User,
        resolution: str,  # "release" | "refund"
        admin_notes: str | None = None,
    ) -> Dispute:
        """Admin resolves a dispute. Delegates escrow release/refund to GigService."""
        if resolution not in ("release", "refund"):
            raise BadRequestError("resolution must be 'release' or 'refund'")

        dispute = await self.db.get(Dispute, dispute_id)
        if not dispute:
            raise NotFoundError("Dispute")
        if dispute.status in (DisputeStatus.RESOLVED_REFUND, DisputeStatus.RESOLVED_RELEASE):
            raise BadRequestError("Dispute already resolved")

        # Delegate order/escrow changes to GigService
        from app.services.gig_service import GigService  # noqa: PLC0415
        gig_svc = GigService(self.db)
        await gig_svc.resolve_dispute(
            order_id=dispute.order_id,
            admin=admin,
            resolution=resolution,
            admin_note=admin_notes or "",
        )

        dispute.status = (
            DisputeStatus.RESOLVED_RELEASE if resolution == "release"
            else DisputeStatus.RESOLVED_REFUND
        )
        dispute.admin_id = admin.id
        dispute.admin_notes = admin_notes
        dispute.resolution = f"Admin {admin.username}: {resolution}"
        dispute.resolved_at = datetime.now(UTC)
        await self.db.commit()

        return await self._load_dispute_by_id(dispute.id)  # type: ignore[return-value]

    async def list_all_disputes(self, status: DisputeStatus | None = None) -> list[Dispute]:
        """Admin: list all disputes with optional status filter."""
        q = (
            select(Dispute)
            .options(selectinload(Dispute.admin))
            .order_by(Dispute.created_at.desc())
        )
        if status:
            q = q.where(Dispute.status == status)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def _load_dispute_by_id(self, dispute_id: uuid.UUID) -> Dispute | None:
        result = await self.db.execute(
            select(Dispute)
            .where(Dispute.id == dispute_id)
            .options(selectinload(Dispute.admin))
        )
        return result.scalar_one_or_none()
