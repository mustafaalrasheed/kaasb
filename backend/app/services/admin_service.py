"""
Kaasb Platform - Admin Service
Platform administration: stats, user management, job moderation, payments.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.user import User, UserRole, UserStatus
from app.models.job import Job, JobStatus
from app.models.contract import Contract, ContractStatus
from app.models.proposal import Proposal
from app.models.payment import Transaction, TransactionType, TransactionStatus, Escrow, EscrowStatus
from app.models.review import Review
from app.models.notification import Notification
from app.models.message import Conversation, Message


class AdminService:
    """Service for admin operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === Platform Statistics ===

    async def get_platform_stats(self) -> dict:
        """Get comprehensive platform statistics."""
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        # User stats
        total_users = (await self.db.execute(
            select(func.count(User.id))
        )).scalar() or 0

        active_users_30d = (await self.db.execute(
            select(func.count(User.id)).where(User.last_login >= thirty_days_ago)
        )).scalar() or 0

        new_users_7d = (await self.db.execute(
            select(func.count(User.id)).where(User.created_at >= seven_days_ago)
        )).scalar() or 0

        users_by_role = dict((await self.db.execute(
            select(User.primary_role, func.count(User.id)).group_by(User.primary_role)
        )).all())

        # Job stats
        total_jobs = (await self.db.execute(
            select(func.count(Job.id))
        )).scalar() or 0

        open_jobs = (await self.db.execute(
            select(func.count(Job.id)).where(Job.status == JobStatus.OPEN)
        )).scalar() or 0

        jobs_7d = (await self.db.execute(
            select(func.count(Job.id)).where(Job.created_at >= seven_days_ago)
        )).scalar() or 0

        # Contract stats
        total_contracts = (await self.db.execute(
            select(func.count(Contract.id))
        )).scalar() or 0

        active_contracts = (await self.db.execute(
            select(func.count(Contract.id)).where(Contract.status == ContractStatus.ACTIVE)
        )).scalar() or 0

        completed_contracts = (await self.db.execute(
            select(func.count(Contract.id)).where(Contract.status == ContractStatus.COMPLETED)
        )).scalar() or 0

        # Proposal stats
        total_proposals = (await self.db.execute(
            select(func.count(Proposal.id))
        )).scalar() or 0

        # Financial stats
        total_volume = (await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.transaction_type == TransactionType.ESCROW_FUND,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )).scalar() or 0.0

        platform_fees = (await self.db.execute(
            select(func.coalesce(func.sum(Transaction.platform_fee), 0.0)).where(
                Transaction.transaction_type == TransactionType.PLATFORM_FEE,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        )).scalar() or 0.0

        pending_escrow = (await self.db.execute(
            select(func.coalesce(func.sum(Escrow.amount), 0.0)).where(
                Escrow.status == EscrowStatus.FUNDED,
            )
        )).scalar() or 0.0

        # Review stats
        avg_rating = (await self.db.execute(
            select(func.avg(Review.rating))
        )).scalar()

        total_reviews = (await self.db.execute(
            select(func.count(Review.id))
        )).scalar() or 0

        # Message stats
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
                "total": total_jobs,
                "open": open_jobs,
                "new_7d": jobs_7d,
            },
            "contracts": {
                "total": total_contracts,
                "active": active_contracts,
                "completed": completed_contracts,
            },
            "proposals": {
                "total": total_proposals,
            },
            "financials": {
                "total_volume": round(total_volume, 2),
                "platform_fees_earned": round(platform_fees, 2),
                "pending_escrow": round(pending_escrow, 2),
            },
            "reviews": {
                "total": total_reviews,
                "average_rating": round(float(avg_rating), 2) if avg_rating else 0.0,
            },
            "messages": {
                "total": total_messages,
            },
        }

    # === User Management ===

    async def list_users(
        self,
        role: Optional[str] = None,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List users with filtering."""
        stmt = select(User)

        if role:
            stmt = stmt.where(User.primary_role == UserRole(role))
        if status_filter:
            stmt = stmt.where(User.status == UserStatus(status_filter))
        if search:
            stmt = stmt.where(
                User.username.ilike(f"%{search}%")
                | User.email.ilike(f"%{search}%")
                | User.first_name.ilike(f"%{search}%")
                | User.last_name.ilike(f"%{search}%")
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(User.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        users = list(result.scalars().all())

        return {
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def update_user_status(
        self, user_id: uuid.UUID, new_status: str
    ) -> User:
        """Admin updates a user's status (active/suspended/deactivated)."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_superuser:
            raise HTTPException(status_code=400, detail="Cannot modify admin status")

        user.status = UserStatus(new_status)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def toggle_superuser(self, user_id: uuid.UUID) -> User:
        """Grant or revoke admin privileges."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_superuser = not user.is_superuser
        if user.is_superuser:
            user.primary_role = UserRole.ADMIN
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # === Job Moderation ===

    async def list_jobs_admin(
        self,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List all jobs for admin moderation."""
        stmt = select(Job).options(selectinload(Job.client))

        if status_filter:
            stmt = stmt.where(Job.status == JobStatus(status_filter))
        if search:
            stmt = stmt.where(
                Job.title.ilike(f"%{search}%")
                | Job.description.ilike(f"%{search}%")
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Job.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        jobs = list(result.scalars().unique().all())

        return {
            "jobs": jobs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    async def update_job_status(
        self, job_id: uuid.UUID, new_status: str
    ) -> Job:
        """Admin updates a job status (e.g., close a fraudulent listing)."""
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        job.status = JobStatus(new_status)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    # === Transaction Overview ===

    async def list_transactions_admin(
        self,
        type_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List all platform transactions."""
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

        return {
            "transactions": transactions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
