"""
Kaasb Platform - Database Session Configuration
Async SQLAlchemy 2.0 with production-safe connection pooling.

Pool sizing for Hetzner CPX22 + Gunicorn (5 UvicornWorkers):
  Each worker is a separate OS process with its own asyncpg pool.
  5 workers × pool_size(5) = 25 baseline connections
  5 workers × (pool_size+max_overflow)(10) = 50 max connections
  PostgreSQL max_connections=75 → 25 headroom for admin/monitoring/Alembic
"""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Per-worker pool capacity — exposed as a constant so the checkout listener
# reports against the configured maximum instead of the asyncpg pool's live
# counters (which report "materialised" connections, not capacity).
_POOL_SIZE = 5
_MAX_OVERFLOW = 5
_POOL_CAPACITY = _POOL_SIZE + _MAX_OVERFLOW

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,       # Never True in production (massive log spam)
    pool_size=_POOL_SIZE,      # Persistent connections per worker (was 20 — pool exhaustion risk)
    max_overflow=_MAX_OVERFLOW, # Burst above pool_size per worker
    pool_pre_ping=True,        # Verify stale connections before handing them out
    pool_recycle=1800,         # Recycle connections every 30 min (prevents firewall drops)
    pool_timeout=30,           # Raise TimeoutError after 30s if pool is exhausted
    connect_args={
        "prepared_statement_cache_size": 256,
        "statement_cache_size": 256,
        "server_settings": {
            # Kill queries running longer than 30 seconds — prevents runaway queries from
            # blocking tables and exhausting the pool. Individual endpoints can override
            # with SET LOCAL statement_timeout for known-slow operations (e.g. migrations).
            "statement_timeout": "30000",           # 30 seconds in milliseconds
            # Kill sessions that hold an open transaction for > 60 seconds.
            # This prevents connection leaks from code that begins a transaction
            # but fails to commit/rollback (e.g. unhandled exceptions before yield).
            "idle_in_transaction_session_timeout": "60000",  # 60 seconds
            # Application name visible in pg_stat_activity — helps identify connections
            "application_name": "kaasb_api",
        },
    },
)

# ── Pool event listeners ────────────────────────────────────────────────────
# Log connection events for pool health monitoring. These listeners attach to
# the underlying sync engine that asyncpg wraps.

@event.listens_for(engine.sync_engine, "connect")
def _on_connect(dbapi_connection, connection_record):
    logger.debug("DB pool: new connection established (pid=%s)", id(dbapi_connection))


@event.listens_for(engine.sync_engine, "checkout")
def _on_checkout(dbapi_connection, connection_record, connection_proxy):
    # Warn when pool is ≥ 80% saturated against the configured max capacity.
    # We compare to the static pool_size+max_overflow because SQLAlchemy's
    # async pool reports live counters (materialised vs in-use) which yield
    # bogus "1/1 100%" warnings when only one connection has been opened.
    try:
        checkedout = connection_proxy._pool.checkedout()
        if checkedout / _POOL_CAPACITY >= 0.8:
            logger.warning(
                "DB pool near exhaustion: %d/%d connections in use (%.0f%%). "
                "Consider scaling pool_size or adding workers.",
                checkedout, _POOL_CAPACITY, 100 * checkedout / _POOL_CAPACITY,
            )
    except Exception:
        pass  # Never let monitoring break request handling


@event.listens_for(engine.sync_engine, "checkin")
def _on_checkin(dbapi_connection, connection_record):
    logger.debug("DB pool: connection returned to pool")


# Session factory — expire_on_commit=False avoids lazy re-loads in async context
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides one database session per request.

    Commits on success, rolls back on any exception.
    The pool returns the connection after the ``async with`` block exits.
    Pool exhaustion (TimeoutError after pool_timeout=30s) is logged as CRITICAL
    so on-call alerts fire before users see 500 errors.
    """
    try:
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    except SATimeoutError:
        logger.critical(
            "DB connection pool exhausted — all %d connections in use. "
            "Requests are queuing. Scale pool_size or investigate slow queries.",
            _POOL_CAPACITY,
        )
        raise


async def init_db() -> None:
    """Create all tables (development only — use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
