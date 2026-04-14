"""
Kaasb Platform - User Service
Business logic for user profiles, search, and account management.
"""

import logging
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import hash_password_async, verify_password_async
from app.models.user import User, UserRole, UserStatus
from app.schemas.user import PasswordChange, UserProfileUpdate
from app.services.base import BaseService
from app.utils.sanitize import escape_like, sanitize_text, sanitize_url

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """Service for user profile and account operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db)

    # === Profile Retrieval ===

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        """Get a user by their UUID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User")
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
            raise NotFoundError("User")
        return user

    # === Profile Update ===

    async def update_profile(
        self, user: User, data: UserProfileUpdate
    ) -> User:
        """Update the user's profile with provided fields."""
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise BadRequestError("No fields to update")

        # Sanitize text fields before applying
        if "bio" in update_data and update_data["bio"] is not None:
            update_data["bio"] = sanitize_text(update_data["bio"], max_length=2000)
        if "display_name" in update_data and update_data["display_name"] is not None:
            update_data["display_name"] = sanitize_text(update_data["display_name"], max_length=100)
        if "title" in update_data and update_data["title"] is not None:
            update_data["title"] = sanitize_text(update_data["title"], max_length=200)
        if "country" in update_data and update_data["country"] is not None:
            update_data["country"] = sanitize_text(update_data["country"], max_length=100)
        if "city" in update_data and update_data["city"] is not None:
            update_data["city"] = sanitize_text(update_data["city"], max_length=100)
        if "portfolio_url" in update_data and update_data["portfolio_url"] is not None:
            update_data["portfolio_url"] = sanitize_url(update_data["portfolio_url"])

        # Validate freelancer-specific fields
        if user.primary_role != UserRole.FREELANCER:
            freelancer_fields = {"title", "hourly_rate", "skills", "experience_level", "portfolio_url"}
            invalid = freelancer_fields & set(update_data.keys())
            if invalid:
                raise BadRequestError(
                    f"Fields {invalid} are only available for freelancer accounts"
                )

        # Apply updates
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        await self.db.refresh(user)
        logger.info("Profile updated: user=%s", user.id)
        return user

    async def update_avatar(self, user: User, avatar_url: str) -> User:
        """Update the user's avatar URL."""
        user.avatar_url = avatar_url
        await self.db.flush()
        await self.db.refresh(user)
        logger.info("Avatar updated: user=%s", user.id)
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
        # Social-login accounts have no password — cannot change what doesn't exist
        if not user.hashed_password:
            raise BadRequestError("This account uses social login and has no password to change")
        # Async bcrypt — prevents blocking the event loop during the ~200ms hash operation
        if not await verify_password_async(data.current_password, user.hashed_password):
            raise BadRequestError("Current password is incorrect")

        if data.current_password == data.new_password:
            raise BadRequestError("New password must be different from current password")

        user.hashed_password = await hash_password_async(data.new_password)
        await self.db.flush()
        logger.info("Password changed: user=%s", user.id)

    # === User Search & Listing ===

    async def search_freelancers(
        self,
        query: str | None = None,
        skills: list[str] | None = None,
        experience_level: str | None = None,
        min_rate: float | None = None,
        max_rate: float | None = None,
        country: str | None = None,
        sort_by: str = "rating",  # rating, rate_low, rate_high, newest
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search freelancers with filters, sorting, and pagination."""
        page_size = self.clamp_page_size(page_size)

        # Build filters once — reused for COUNT and SELECT (no subquery overhead)
        filters = [
            User.primary_role == UserRole.FREELANCER,
            User.status == UserStatus.ACTIVE,
        ]

        if query:
            search_term = f"%{escape_like(query[:200])}%"
            filters.append(or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.title.ilike(search_term),
                User.bio.ilike(search_term),
                User.username.ilike(search_term),
            ))
        if skills:
            filters.append(User.skills.overlap(skills))
        if experience_level:
            filters.append(User.experience_level == experience_level)
        if min_rate is not None:
            filters.append(User.hourly_rate >= min_rate)
        if max_rate is not None:
            filters.append(User.hourly_rate <= max_rate)
        if country:
            filters.append(User.country.ilike(f"%{escape_like(country[:100])}%"))

        # Direct COUNT — uses ix_users_freelancer_active partial index (~2x faster)
        total = (await self.db.execute(
            select(func.count(User.id)).where(*filters)
        )).scalar() or 0

        # Data query with sorting
        stmt = select(User).where(*filters)

        if sort_by == "rate_low":
            stmt = stmt.order_by(User.hourly_rate.asc().nullslast())
        elif sort_by == "rate_high":
            stmt = stmt.order_by(User.hourly_rate.desc().nullslast())
        elif sort_by == "newest":
            stmt = stmt.order_by(User.created_at.desc())
        else:  # rating (default)
            stmt = stmt.order_by(User.avg_rating.desc(), User.total_reviews.desc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(stmt)
        users = result.scalars().all()

        return self.paginated_response(items=list(users), total=total, page=page, page_size=page_size, key="users")

    # === Account Management ===

    async def deactivate_account(self, user: User) -> None:
        """Deactivate a user's account."""
        user.status = UserStatus.DEACTIVATED
        user.is_online = False
        await self.db.flush()
        logger.info("Account deactivated: user=%s", user.id)
