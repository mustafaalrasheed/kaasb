"""
Kaasb Platform - User Service
Business logic for user profiles, search, and account management.
"""

import uuid
from typing import Optional

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User, UserRole, UserStatus
from app.schemas.user import UserProfileUpdate, PasswordChange
from app.core.security import hash_password, verify_password


class UserService:
    """Service for user profile and account operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # === Profile Retrieval ===

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        """Get a user by their UUID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_by_username(self, username: str) -> User:
        """Get a user by their username (public profile)."""
        result = await self.db.execute(
            select(User).where(
                User.username == username,
                User.status == UserStatus.ACTIVE,
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    # === Profile Update ===

    async def update_profile(
        self, user: User, data: UserProfileUpdate
    ) -> User:
        """Update the user's profile with provided fields."""
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update",
            )

        # Validate freelancer-specific fields
        if user.primary_role != UserRole.FREELANCER:
            freelancer_fields = {"title", "hourly_rate", "skills", "experience_level", "portfolio_url"}
            invalid = freelancer_fields & set(update_data.keys())
            if invalid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Fields {invalid} are only available for freelancer accounts",
                )

        # Apply updates
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_avatar(self, user: User, avatar_url: str) -> User:
        """Update the user's avatar URL."""
        user.avatar_url = avatar_url
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def remove_avatar(self, user: User) -> User:
        """Remove the user's avatar."""
        user.avatar_url = None
        await self.db.flush()
        await self.db.refresh(user)
        return user

    # === Password Change ===

    async def change_password(self, user: User, data: PasswordChange) -> None:
        """Change the user's password after verifying the current one."""
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        if data.current_password == data.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        user.hashed_password = hash_password(data.new_password)
        await self.db.flush()

    # === User Search & Listing ===

    async def search_freelancers(
        self,
        query: Optional[str] = None,
        skills: Optional[list[str]] = None,
        experience_level: Optional[str] = None,
        min_rate: Optional[float] = None,
        max_rate: Optional[float] = None,
        country: Optional[str] = None,
        sort_by: str = "rating",  # rating, rate_low, rate_high, newest
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search freelancers with filters, sorting, and pagination."""
        stmt = select(User).where(
            User.primary_role == UserRole.FREELANCER,
            User.status == UserStatus.ACTIVE,
        )

        # Text search on name, title, bio, skills
        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.title.ilike(search_term),
                    User.bio.ilike(search_term),
                    User.username.ilike(search_term),
                )
            )

        # Filter by skills (ANY match)
        if skills:
            stmt = stmt.where(User.skills.overlap(skills))

        # Filter by experience level
        if experience_level:
            stmt = stmt.where(User.experience_level == experience_level)

        # Filter by hourly rate range
        if min_rate is not None:
            stmt = stmt.where(User.hourly_rate >= min_rate)
        if max_rate is not None:
            stmt = stmt.where(User.hourly_rate <= max_rate)

        # Filter by country
        if country:
            stmt = stmt.where(User.country.ilike(f"%{country}%"))

        # Count total results
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Sorting
        if sort_by == "rate_low":
            stmt = stmt.order_by(User.hourly_rate.asc().nullslast())
        elif sort_by == "rate_high":
            stmt = stmt.order_by(User.hourly_rate.desc().nullslast())
        elif sort_by == "newest":
            stmt = stmt.order_by(User.created_at.desc())
        else:  # rating (default)
            stmt = stmt.order_by(User.avg_rating.desc(), User.total_reviews.desc())

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self.db.execute(stmt)
        users = result.scalars().all()

        return {
            "users": list(users),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    # === Account Management ===

    async def deactivate_account(self, user: User) -> None:
        """Deactivate a user's account."""
        user.status = UserStatus.DEACTIVATED
        user.is_online = False
        await self.db.flush()
