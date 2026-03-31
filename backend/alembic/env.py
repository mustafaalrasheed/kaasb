"""
Kaasb Platform - Alembic Environment Configuration
Supports async PostgreSQL migrations with SQLAlchemy 2.0.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from alembic import context

from app.core.config import get_settings
from app.core.database import Base

# Import all models so Alembic can detect them
from app.models import *  # noqa: F401, F403

settings = get_settings()

# Alembic Config object
config = context.config

# Override sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects included in autogenerate comparisons.

    Two categories of DB objects are intentionally excluded from comparison:

    1. Performance indexes (c7d4e8f2a901) — composite/partial/descending indexes
       added via a dedicated migration but NOT declared in model __table_args__,
       to keep model definitions readable.

    2. audit_log table (e2b3c4d5e6f7) — append-only compliance ledger with no
       SQLAlchemy model (it is written to via raw SQL triggers, not the ORM).

    Rule: skip any object that exists in the database but has no counterpart in
    the ORM model metadata (reflected=True, compare_to=None).
    Objects defined in models but missing from the DB are still reported normally,
    so the check continues to catch un-migrated model additions.
    """
    if reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with sync engine."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
