"""
Kaasb Platform - Admin Audit Service

Append-only admin-action log. Call `AuditService.log(...)` from any service
that performs a privileged admin action so every action is traceable to
admin + IP + timestamp + target.

Writes are best-effort — a failure to write an audit entry MUST NOT break
the underlying action. Errors are logged to the application log; if an
admin action completes but its audit entry fails, the action still succeeds.
That tradeoff is intentional: silently swallowing an escrow release because
the audit table is unavailable would be worse than a missing audit row.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_audit import AdminAuditAction, AdminAuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Writes admin audit log entries. All methods are fire-and-forget-safe."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        admin_id: uuid.UUID | None,
        action: AdminAuditAction,
        target_type: str,
        target_id: uuid.UUID | None = None,
        amount: float | None = None,
        currency: str | None = None,
        ip_address: str | None = None,
        details: dict | None = None,
    ) -> AdminAuditLog | None:
        """
        Write one audit entry. Returns the inserted row, or None on failure
        (never raises — callers don't need a try/except around this).
        """
        try:
            entry = AdminAuditLog(
                admin_id=admin_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                amount=amount,
                currency=currency,
                ip_address=ip_address,
                details=details,
            )
            self.db.add(entry)
            await self.db.flush()
            return entry
        except Exception:
            logger.exception(
                "audit: failed to write log entry (admin=%s action=%s target=%s/%s)",
                admin_id, action.value, target_type, target_id,
            )
            return None

    async def list_recent(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[AdminAuditLog], int]:
        """List recent audit log entries. Returns (rows, total_count)."""
        from sqlalchemy import func as _func

        total_result = await self.db.execute(select(_func.count(AdminAuditLog.id)))
        total = total_result.scalar_one() or 0

        result = await self.db.execute(
            select(AdminAuditLog)
            .order_by(AdminAuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total
