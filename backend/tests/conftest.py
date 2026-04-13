"""
Kaasb Platform - Test Configuration
Shared fixtures for all tests.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole, UserStatus
from app.core.security import hash_password

# Use the PostgreSQL service from CI (DATABASE_URL env var).
# SQLite cannot handle PostgreSQL-specific types (ARRAY, UUID, enums).
import os
_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db",
)

test_engine = create_async_engine(_db_url, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop after using CASCADE."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        # CASCADE handles FK dependencies PostgreSQL enforces
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC"))


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with DB override."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_client_user(db_session: AsyncSession) -> User:
    """Create a sample client user for testing."""
    user = User(
        id=uuid.uuid4(),
        email="client@test.com",
        username="testclient",
        hashed_password=hash_password("TestPass1!"),
        first_name="Test",
        last_name="Client",
        primary_role=UserRole.CLIENT,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def sample_freelancer_user(db_session: AsyncSession) -> User:
    """Create a sample freelancer user for testing."""
    user = User(
        id=uuid.uuid4(),
        email="freelancer@test.com",
        username="testfreelancer",
        hashed_password=hash_password("TestPass1!"),
        first_name="Test",
        last_name="Freelancer",
        primary_role=UserRole.FREELANCER,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
        hourly_rate=50.0,
        skills=["Python", "FastAPI"],
        title="Senior Developer",
    )
    db_session.add(user)
    await db_session.flush()
    return user
