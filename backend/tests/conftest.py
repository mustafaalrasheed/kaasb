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
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole, UserStatus
from app.core.security import hash_password

# In-memory SQLite for tests (fast, isolated)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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
