"""
Kaasb Platform - Create Admin User
Run: python -m scripts.create_admin

Environment variable overrides (for non-interactive / CI use):
  ADMIN_EMAIL     default: admin@kaasb.com
  ADMIN_USERNAME  default: admin
  ADMIN_PASSWORD  required when running non-interactively (no default)
"""

import asyncio
import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import async_session as async_session_factory
from app.models.user import User, UserRole, UserStatus
from app.core.security import hash_password


async def create_admin(
    email: str,
    username: str,
    password: str,
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
            is_email_verified=True,
        )
        db.add(admin)
        await db.commit()
        print(f"✅ Admin user created:")
        print(f"   Email:    {email}")
        print(f"   Username: {username}")
        print(f"   ⚠️  Change the password after first login!")


if __name__ == "__main__":
    # Prefer env vars (safe for automated deploys); fall back to interactive input
    env_email    = os.environ.get("ADMIN_EMAIL", "")
    env_username = os.environ.get("ADMIN_USERNAME", "")
    env_password = os.environ.get("ADMIN_PASSWORD", "")

    email    = env_email    or input("Admin email [admin@kaasb.com]: ").strip() or "admin@kaasb.com"
    username = env_username or input("Admin username [admin]: ").strip() or "admin"

    if env_password:
        password = env_password
    else:
        import getpass
        password = getpass.getpass("Admin password: ").strip()
        if not password:
            print("ERROR: Password cannot be empty.", file=sys.stderr)
            sys.exit(1)

    asyncio.run(create_admin(email, username, password))
