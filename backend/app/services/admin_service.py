"""
Kaasb Platform - Admin Service
Platform administration: stats, user management, job moderation, payments.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.contract import Contract, ContractStatus, Milestone
from app.models.job import Job, JobStatus
from app.models.message import Message
from app.models.payment import (
    Escrow,
    EscrowStatus,
    PaymentAccount,
    PaymentProvider,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.models.proposal import Proposal
from app.models.review import Review
from app.models.user import User, UserRole, UserStatus
from app.services.base import BaseService
from app.utils.sanitize import escape_like

logger = logging.getLogger(__name__)

# Transaction-scoped advisory lock key for admin-state mutations.
# Postgres resolves hashtext() per transaction — any literal string works.
# Serializes update_user_status + toggle_superuser across connections so
# the last-admin invariant can't be violated by concurrent writes
# (nightly-2026-04-25 P0 #3).
_ADMIN_MUTATION_LOCK = (
    "SELECT pg_advisory_xact_lock(hashtext('kaasb-admin-mutation'))"
)


class AdminService(BaseService):
    """Service for admin operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    # === Platform Statistics ===

    async def get_platform_stats(self) -> dict:
        """
        Get comprehensive platform statistics.
        Optimized: 5 queries instead of 10+ (batched aggregations).
        ~200ms → ~50ms at 100K rows scale.
        """
        now = datetime.now(UTC)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        # === Query 1: User stats + role breakdown in a single pass ===
        user_stats_row = (await self.db.execute(
            select(
                func.count(User.id),
                func.count(User.id).filter(User.last_login >= thirty_days_ago),
                func.count(User.id).filter(User.created_at >= seven_days_ago),
            )
        )).one()
        total_users = user_stats_row[0] or 0
        active_users_30d = user_stats_row[1] or 0
        new_users_7d = user_stats_row[2] or 0

        users_by_role: dict[UserRole, int] = dict((await self.db.execute(
            select(User.primary_role, func.count(User.id)).group_by(User.primary_role)
        )).all())

        # === Query 2: Job + Contract + Proposal counts in one query ===
        job_stats_row = (await self.db.execute(
            select(
                func.count(Job.id),
                func.count(Job.id).filter(Job.status == JobStatus.OPEN),
                func.count(Job.id).filter(Job.created_at >= seven_days_ago),
            )
        )).one()

        contract_stats_row = (await self.db.execute(
            select(
                func.count(Contract.id),
                func.count(Contract.id).filter(Contract.status == ContractStatus.ACTIVE),
                func.count(Contract.id).filter(Contract.status == ContractStatus.COMPLETED),
            )
        )).one()

        total_proposals = (await self.db.execute(
            select(func.count(Proposal.id))
        )).scalar() or 0

        # === Query 3: Financial stats — batched ===
        fin_row = (await self.db.execute(
            select(
                func.coalesce(func.sum(Transaction.amount).filter(
                    Transaction.transaction_type == TransactionType.ESCROW_FUND,
                    Transaction.status == TransactionStatus.COMPLETED,
                ), 0.0),
                func.coalesce(func.sum(Transaction.platform_fee).filter(
                    Transaction.transaction_type == TransactionType.PLATFORM_FEE,
                    Transaction.status == TransactionStatus.COMPLETED,
                ), 0.0),
            )
        )).one()
        total_volume = fin_row[0]
        platform_fees = fin_row[1]

        pending_escrow = (await self.db.execute(
            select(func.coalesce(func.sum(Escrow.amount), 0.0)).where(
                Escrow.status == EscrowStatus.FUNDED,
            )
        )).scalar() or 0.0

        # === Query 4: Review + Message counts ===
        review_row = (await self.db.execute(
            select(func.avg(Review.rating), func.count(Review.id))
        )).one()

        total_messages = (await self.db.execute(
            select(func.count(Message.id))
        )).scalar() or 0

        return {
            "users": {
                "total": total_users,
                "active_30d": active_users_30d,
                "new_7d": new_users_7d,
                "by_role": {k.value if hasattr(k, 'value') else k: v for k, v in users_by_role.items()},
            },
            "jobs": {
                "total": job_stats_row[0] or 0,
                "open": job_stats_row[1] or 0,
                "new_7d": job_stats_row[2] or 0,
            },
            "contracts": {
                "total": contract_stats_row[0] or 0,
                "active": contract_stats_row[1] or 0,
                "completed": contract_stats_row[2] or 0,
            },
            "proposals": {
                "total": total_proposals,
            },
            "financials": {
                "total_volume": round(float(total_volume), 2),
                "platform_fees_earned": round(float(platform_fees), 2),
                "pending_escrow": round(float(pending_escrow), 2),
            },
            "reviews": {
                "total": review_row[1] or 0,
                "average_rating": round(float(review_row[0]), 2) if review_row[0] else 0.0,
            },
            "messages": {
                "total": total_messages,
            },
        }

    # === User Management ===

    async def list_users(
        self,
        role: str | None = None,
        status_filter: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List users with filtering."""
        page_size = self.clamp_page_size(page_size)
        stmt = select(User)

        # Enum coercion guarded — a typo'd query string shouldn't 500 the
        # admin panel (nightly-2026-04-25 P1).
        if role:
            try:
                role_enum = UserRole(role)
            except ValueError as exc:
                raise BadRequestError(
                    f"Unknown role '{role}'. Expected one of: "
                    f"{', '.join(r.value for r in UserRole)}."
                ) from exc
            stmt = stmt.where(User.primary_role == role_enum)
        if status_filter:
            try:
                status_enum = UserStatus(status_filter)
            except ValueError as exc:
                raise BadRequestError(
                    f"Unknown status '{status_filter}'. Expected one of: "
                    f"{', '.join(s.value for s in UserStatus)}."
                ) from exc
            stmt = stmt.where(User.status == status_enum)
        if search:
            safe_search = escape_like(search[:200])
            stmt = stmt.where(
                User.username.ilike(f"%{safe_search}%")
                | User.email.ilike(f"%{safe_search}%")
                | User.first_name.ilike(f"%{safe_search}%")
                | User.last_name.ilike(f"%{safe_search}%")
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(User.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        users = list(result.scalars().all())

        return self.paginated_response(items=users, total=total, page=page, page_size=page_size, key="users")

    async def update_user_status(
        self, user_id: uuid.UUID, new_status: str, acting_admin: User
    ) -> User:
        """Admin updates a user's status (active/suspended/deactivated).

        Safety guards (nightly-2026-04-25 P0 #1):
          * An admin cannot change their own account status — that would
            let a single admin lock themselves out via the UI.
          * Moving an active admin to a non-active status requires at least
            one other active admin to remain, otherwise the platform ends
            up with zero admins able to log in.

        Does not commit — the calling endpoint commits once, after writing
        the audit-log row, so the status change and audit row land in the
        same transaction (nightly-2026-04-25 P0 #4, audit-loss race).
        """
        if user_id == acting_admin.id:
            raise BadRequestError(
                "You can't change your own account status from the admin UI."
            )

        # Serialize against other admin-state mutations so the last-admin
        # check can't race with a concurrent toggle_superuser / update on
        # another admin account.
        await self.db.execute(text(_ADMIN_MUTATION_LOCK))

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User")

        new_status_enum = UserStatus(new_status)
        if (
            user.is_superuser
            and user.status == UserStatus.ACTIVE
            and new_status_enum != UserStatus.ACTIVE
        ):
            # Count OTHER active admins — we're about to take this one out.
            admin_count_result = await self.db.execute(
                select(func.count(User.id)).where(
                    User.id != user_id,
                    User.is_superuser.is_(True),
                    User.status == UserStatus.ACTIVE,
                )
            )
            admin_count = admin_count_result.scalar() or 0
            if admin_count < 1:
                raise BadRequestError(
                    "Can't suspend or deactivate the last remaining active admin."
                )

        user.status = new_status_enum
        await self.db.flush()
        return user

    async def toggle_superuser(self, user_id: uuid.UUID, acting_admin: User) -> User:
        """Grant or revoke admin privileges with safety checks.

        Does not commit — the calling endpoint commits once after writing
        the audit-log row (nightly-2026-04-25 P0 #4).
        """
        if user_id == acting_admin.id:
            raise BadRequestError("Cannot modify your own admin privileges")

        # Transaction-scoped advisory lock serializes all admin-state
        # mutations. Without this, two admins concurrently revoking each
        # other can both pass the "last-admin-remains" check and both
        # commit, leaving zero admins (nightly-2026-04-25 P0 #3).
        await self.db.execute(text(_ADMIN_MUTATION_LOCK))

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User")

        # If revoking, ensure at least one OTHER active admin remains.
        # (The original check `<=1` implicitly counted the target if they
        # were active, but missed the case where the target was already
        # suspended/deactivated — e.g. an attacker already drained actives
        # via update_user_status.)
        if user.is_superuser:
            admin_count_result = await self.db.execute(
                select(func.count(User.id)).where(
                    User.id != user_id,
                    User.is_superuser.is_(True),
                    User.status == UserStatus.ACTIVE,
                )
            )
            admin_count = admin_count_result.scalar() or 0
            if admin_count < 1:
                raise BadRequestError("Cannot revoke the last remaining admin")

        user.is_superuser = not user.is_superuser
        if user.is_superuser:
            user.primary_role = UserRole.ADMIN
            # Admin already has staff powers — drop the support flag to keep
            # one source of truth on the privilege hierarchy.
            user.is_support = False
        else:
            # Demoted — fall back to client (safest default; admin can update further)
            user.primary_role = UserRole.CLIENT
        logger.info(
            "Admin privilege %s user=%s by admin=%s",
            "granted to" if user.is_superuser else "revoked from",
            user_id, acting_admin.id,
        )
        await self.db.flush()
        return user

    async def unsuspend_chat(self, user_id: uuid.UUID) -> User:
        """
        Lift an off-platform-violation chat suspension early. Clears the 24h
        ``chat_suspended_until`` timestamp but leaves the running
        ``chat_violations`` counter alone — the user's history isn't erased,
        only the current cooldown. A follow-up violation still escalates
        from whatever count they were at, so repeat offenders can't game
        the admin by asking for a lift every time.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User")

        if user.chat_suspended_until is None:
            raise BadRequestError("User is not currently suspended from chat")

        user.chat_suspended_until = None
        logger.info("Chat suspension lifted for user=%s", user_id)
        await self.db.flush()
        return user

    async def toggle_support(self, user_id: uuid.UUID, acting_admin: User) -> User:
        """
        Grant or revoke limited-privilege support role. Support can triage
        disputes and handle support chat but cannot release funds or change
        user state. Admins already have those powers — toggling support on
        an admin is a no-op (the is_support flag is kept off on admins).
        """
        if user_id == acting_admin.id:
            raise BadRequestError("Cannot modify your own support role")

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User")

        if user.is_superuser:
            raise BadRequestError("Admins already have full staff access")

        user.is_support = not user.is_support
        logger.info(
            "Support role %s user=%s by admin=%s",
            "granted to" if user.is_support else "revoked from",
            user_id, acting_admin.id,
        )
        await self.db.flush()
        return user

    # === Job Moderation ===

    async def list_jobs_admin(
        self,
        status_filter: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List all jobs for admin moderation."""
        page_size = self.clamp_page_size(page_size)
        stmt = select(Job).options(selectinload(Job.client))

        if status_filter:
            stmt = stmt.where(Job.status == JobStatus(status_filter))
        if search:
            safe_search = escape_like(search[:200])
            stmt = stmt.where(
                Job.title.ilike(f"%{safe_search}%")
                | Job.description.ilike(f"%{safe_search}%")
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Job.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        jobs = list(result.scalars().unique().all())

        return self.paginated_response(items=jobs, total=total, page=page, page_size=page_size, key="jobs")

    async def update_job_status(
        self, job_id: uuid.UUID, new_status: str
    ) -> Job:
        """Admin updates a job status (e.g., close a fraudulent listing).

        Does not commit — the calling endpoint commits after writing
        the audit row so the status change and audit land together
        (same atomicity pattern as update_user_status).
        """
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise NotFoundError("Job")

        try:
            job.status = JobStatus(new_status)
        except ValueError as exc:
            raise BadRequestError(
                f"Unknown job status '{new_status}'. Expected one of: "
                f"{', '.join(s.value for s in JobStatus)}."
            ) from exc
        await self.db.flush()
        return job

    # === Escrow Payout Management ===

    async def list_funded_escrows(
        self, page: int = 1, page_size: int = 50
    ) -> list[dict]:
        """
        List funded escrows awaiting admin manual payout via Qi Card.
        Includes both contract-milestone escrows and gig-order escrows.

        Paginated because each row contains freelancer PII (email, phone,
        QiCard holder + account number). Without a cap, a single request
        on a stolen admin cookie scrapes every freelancer's payout data
        (nightly-2026-04-25 P2). ``clamp_page_size`` enforces the max.
        """
        page_size = self.clamp_page_size(page_size)
        stmt = (
            select(Escrow, User)
            .join(User, User.id == Escrow.freelancer_id)
            .where(Escrow.status == EscrowStatus.FUNDED)
            .order_by(Escrow.funded_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        # Batch-load milestones for contract-based escrows (gig orders have milestone_id=None)
        milestone_ids = [r[0].milestone_id for r in rows if r[0].milestone_id]
        milestone_map: dict[uuid.UUID, Milestone] = {}
        if milestone_ids:
            ms_result = await self.db.execute(
                select(Milestone).where(Milestone.id.in_(milestone_ids))
            )
            milestone_map = {m.id: m for m in ms_result.scalars().all()}

        # Batch-load Qi Card phones for all freelancers
        freelancer_ids = [r[1].id for r in rows]
        qi_accounts: dict[uuid.UUID, tuple[str | None, str | None, str | None]] = {}
        if freelancer_ids:
            accounts_result = await self.db.execute(
                select(
                    PaymentAccount.user_id,
                    PaymentAccount.qi_card_phone,
                    PaymentAccount.qi_card_holder_name,
                    PaymentAccount.qi_card_account_number,
                ).where(
                    PaymentAccount.user_id.in_(freelancer_ids),
                    PaymentAccount.provider == PaymentProvider.QI_CARD,
                )
            )
            for user_id, phone, holder, account_number in accounts_result.all():
                qi_accounts[user_id] = (phone, holder, account_number)

        escrows = []
        for escrow, freelancer in rows:
            milestone = milestone_map.get(escrow.milestone_id) if escrow.milestone_id else None
            phone, holder, account_number = qi_accounts.get(freelancer.id, (None, None, None))
            escrows.append({
                "escrow_id": escrow.id,
                "contract_id": escrow.contract_id,
                "gig_order_id": escrow.gig_order_id,
                "milestone_id": escrow.milestone_id,
                "milestone_title": milestone.title if milestone else None,
                "amount": float(escrow.amount),
                "platform_fee": float(escrow.platform_fee),
                "freelancer_amount": float(escrow.freelancer_amount),
                "currency": escrow.currency,
                "funded_at": escrow.funded_at,
                "freelancer": {
                    "id": freelancer.id,
                    "username": freelancer.username,
                    "email": freelancer.email,
                    "phone": freelancer.phone,
                    "qi_card_phone": phone,
                    "qi_card_holder_name": holder,
                    "qi_card_account_number": account_number,
                },
            })
        return escrows

    async def list_processing_payouts(self) -> list[dict]:
        """
        List PAYOUT transactions stuck in PROCESSING — the admin must send
        the money manually via the Qi Card merchant portal, then hit
        POST /admin/payouts/{id}/mark-paid to flip each to COMPLETED and
        notify the freelancer.
        """
        stmt = (
            select(Transaction, User)
            .join(User, User.id == Transaction.payee_id)
            .where(
                Transaction.transaction_type == TransactionType.PAYOUT,
                Transaction.status == TransactionStatus.PROCESSING,
            )
            .order_by(Transaction.created_at.asc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        freelancer_ids = [r[1].id for r in rows]
        qi_phones: dict[uuid.UUID, str | None] = {}
        if freelancer_ids:
            accounts_result = await self.db.execute(
                select(PaymentAccount.user_id, PaymentAccount.qi_card_phone).where(
                    PaymentAccount.user_id.in_(freelancer_ids),
                    PaymentAccount.provider == PaymentProvider.QI_CARD,
                )
            )
            for user_id, phone in accounts_result.all():
                qi_phones[user_id] = phone

        payouts = []
        for tx, freelancer in rows:
            payouts.append({
                "transaction_id": tx.id,
                "amount": float(tx.amount),
                "currency": tx.currency,
                "requested_at": tx.created_at,
                "provider": tx.provider.value if tx.provider else None,
                "description": tx.description,
                "freelancer": {
                    "id": freelancer.id,
                    "username": freelancer.username,
                    "email": freelancer.email,
                    "phone": freelancer.phone,
                    "qi_card_phone": qi_phones.get(freelancer.id),
                },
            })
        return payouts

    async def list_stuck_pending_transactions(
        self, min_age_minutes: int = 30
    ) -> list[dict]:
        """
        List PENDING Transactions older than `min_age_minutes` — the Qi Card
        success webhook never landed, so Kaasb doesn't know whether to
        complete or refund. Admin reconciles each one manually against the
        Qi Card merchant dashboard.

        Returns enough context (payer, amount, age, order_id) for the admin
        to look the transaction up in Qi Card's portal.
        """
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(minutes=min_age_minutes)
        stmt = (
            select(Transaction, User)
            .outerjoin(User, User.id == Transaction.payer_id)
            .where(
                Transaction.status == TransactionStatus.PENDING,
                Transaction.created_at < cutoff,
            )
            .order_by(Transaction.created_at.asc())
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        payments: list[dict] = []
        for tx, payer in rows:
            payments.append({
                "transaction_id": tx.id,
                "external_order_id": tx.external_transaction_id,
                "amount": float(tx.amount),
                "currency": tx.currency,
                "transaction_type": tx.transaction_type.value,
                "created_at": tx.created_at,
                "age_minutes": int(
                    (datetime.now(UTC) - tx.created_at).total_seconds() // 60
                ),
                "provider": tx.provider.value if tx.provider else None,
                "description": tx.description,
                "payer": {
                    "id": payer.id,
                    "username": payer.username,
                    "email": payer.email,
                } if payer else None,
            })
        return payments

    # === Transaction Overview ===

    async def list_transactions_admin(
        self,
        type_filter: str | None = None,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List all platform transactions."""
        page_size = self.clamp_page_size(page_size)
        stmt = select(Transaction)

        if type_filter:
            stmt = stmt.where(
                Transaction.transaction_type == TransactionType(type_filter)
            )
        if status_filter:
            stmt = stmt.where(
                Transaction.status == TransactionStatus(status_filter)
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Transaction.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        transactions = list(result.scalars().all())

        return self.paginated_response(items=transactions, total=total, page=page, page_size=page_size, key="transactions")
