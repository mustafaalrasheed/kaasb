"""Composite (user_id, is_read) index on notifications

Revision ID: b4w5x6y7z8a9
Revises: a3v4w5x6y7z8
Create Date: 2026-04-21

Every unread-count query and the dashboard's "filter by unread" listing
filters on both user_id and is_read. The single-column indexes created
in the original notifications migration force PostgreSQL to pick one
and post-filter the other. A composite index on (user_id, is_read)
covers both paths and keeps the /unread-count hot path latency flat
as notification volume grows.
"""

from alembic import op

revision = "b4w5x6y7z8a9"
down_revision = "a3v4w5x6y7z8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_notifications_user_is_read",
        "notifications",
        ["user_id", "is_read"],
    )
    # The two single-column indexes (user_id, is_read) are now redundant —
    # the composite above covers queries on user_id alone via the leftmost
    # prefix rule, and every is_read query also filters on user_id.
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")


def downgrade() -> None:
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.drop_index("ix_notifications_user_is_read", table_name="notifications")
