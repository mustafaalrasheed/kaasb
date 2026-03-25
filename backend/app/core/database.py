"""
Kaasb Platform - Database Session Configuration
Async SQLAlchemy 2.0 setup with optimized connection pooling.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# Create async engine with optimized connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL in dev mode (WARNING: huge perf hit — ensure DEBUG=False in prod)
    pool_size=20,          # Persistent connections (matches typical Uvicorn worker concurrency)
    max_overflow=10,       # Burst capacity above pool_size
    pool_pre_ping=True,    # Verify connections before use (prevents stale connection errors)
    pool_recycle=1800,     # Recycle every 30min (was 1hr — reduces stale conn risk behind PgBouncer/firewalls)
    pool_timeout=30,       # Raise after 30s if no connection available
    # Performance: disable implicit RETURNING on INSERT (asyncpg already handles this efficiently)
    # Prepared statement cache — asyncpg default is 100, increase for apps with many distinct queries
    connect_args={
        "prepared_statement_cache_size": 256,  # Cache more prepared statements (default: 100)
        "statement_cache_size": 256,            # asyncpg statement cache (avoids re-parsing SQL)
    },
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Avoid lazy re-loads after commit (key for async perf)
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session per request.

    The session auto-commits on success and rolls back on error.
    Cleanup is handled by the ``async with`` context manager.

    Usage::

        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables (for development only - use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
