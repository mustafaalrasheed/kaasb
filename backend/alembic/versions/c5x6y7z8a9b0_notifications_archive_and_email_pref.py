"""Notifications archive column + user email-notification toggle

Revision ID: c5x6y7z8a9b0
Revises: b4w5x6y7z8a9
Create Date: 2026-04-21

Two schema additions that back PR-N4:

1. notifications.archived_at — soft-delete timestamp. The data retention
   task now sets archived_at instead of hard-DELETE so GDPR export stays
   complete and the admin can audit history when a dispute surfaces later.
   Active queries filter `archived_at IS NULL` so the bell/list behaviour
   is unchanged.

2. users.email_notifications_enabled — a single per-user opt-out toggle.
   The service layer consults this before sending any notification email
   via Resend. Granular per-type preferences are deferred to a later PR.
"""

import sqlalchemy as sa

from alembic import op

revision = "c5x6y7z8a9b0"
down_revision = "b4w5x6y7z8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notifications_archived_at",
        "notifications",
        ["archived_at"],
    )
    op.add_column(
        "users",
        sa.Column(
            "email_notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "email_notifications_enabled")
    op.drop_index("ix_notifications_archived_at", table_name="notifications")
    op.drop_column("notifications", "archived_at")
