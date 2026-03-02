"""
Kaasb Platform - Create Admin User
Run: python -m scripts.create_admin
"""

import asyncio
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.user import User, UserRole, UserStatus
from app.core.security import hash_password


async def create_admin(
    email: str = "admin@kaasb.com",
    username: str = "admin",
    password: str = "AdminPass123!",
    first_name: str = "Platform",
    last_name: str = "Admin",
):
    """Create an admin user."""
    async with async_session_factory() as db:
        # Check if exists
        result = await db.execute(
            select(User).where(User.email == email)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"User {email} already exists. Updating to admin...")
            existing.is_superuser = True
            existing.primary_role = UserRole.ADMIN
            await db.commit()
            print(f"✅ {email} is now admin")
            return

        admin = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            primary_role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_superuser=True,
            is_verified=True,
        )
        db.add(admin)
        await db.commit()
        print(f"✅ Admin user created:")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   ⚠️  Change the password after first login!")


if __name__ == "__main__":
    email = input("Admin email [admin@kaasb.com]: ").strip() or "admin@kaasb.com"
    username = input("Admin username [admin]: ").strip() or "admin"
    password = input("Admin password [AdminPass123!]: ").strip() or "AdminPass123!"

    asyncio.run(create_admin(email, username, password))
