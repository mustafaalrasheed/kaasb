"""Add JOB_STATUS_CHANGED to adminauditaction enum

Revision ID: g9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-04-25

nightly-2026-04-25 P1: admin job-moderation writes no audit row. Same
shape as USER_STATUS_CHANGED — we want a dedicated enum variant (not a
reused one) so alerting/reporting queries that filter on
``action = 'user_status_changed'`` don't get confused by job actions.
"""

from alembic import op

revision = "g9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE can't run inside a transaction in Postgres
    # older than 12 and stays safer to run outside one in all versions.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE adminauditaction ADD VALUE IF NOT EXISTS 'job_status_changed'"
        )


def downgrade() -> None:
    # Postgres does not support DROP VALUE on an enum. Leaving the variant
    # in place on downgrade is standard practice — nothing references it
    # once the code rolls back.
    pass
