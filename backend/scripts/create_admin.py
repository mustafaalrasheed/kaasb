"""
Kaasb Platform - Create / Reset Admin User
Run: python -m scripts.create_admin

Environment variable overrides (for non-interactive / CI use):
  ADMIN_EMAIL     default: admin@kaasb.com
  ADMIN_USERNAME  default: admin
  ADMIN_PASSWORD  required when running non-interactively (no default)
  ADMIN_RESET     set to "1" to reset password of existing admin
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


async def create_or_reset_admin(
    email: str,
    username: str,
    password: str,
    reset: bool = False,
    first_name: str = "Platform",
    last_name: str = "Admin",
):
    """Create a new admin user, promote an existing user, or reset their password."""
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            existing.is_superuser = True
            existing.primary_role = UserRole.ADMIN
            existing.status = UserStatus.ACTIVE
            existing.failed_login_attempts = 0
            existing.locked_until = None
            if reset:
                existing.hashed_password = hash_password(password)
                await db.commit()
                print(f"✅ Password reset for {email}")
            else:
                await db.commit()
                print(f"✅ {email} is now admin (password unchanged)")
                print("   Run with --reset to also change the password.")
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
    env_reset    = os.environ.get("ADMIN_RESET", "") == "1" or "--reset" in sys.argv

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

    asyncio.run(create_or_reset_admin(email, username, password, reset=env_reset))
