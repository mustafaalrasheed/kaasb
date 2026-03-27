"""legal_compliance

Adds tables and indexes for Prompt 11 — Legal & Compliance:

1. reports table — content moderation reports (jobs, users, messages, reviews)
2. Enum types: report_type, report_reason, report_status

Revision ID: f3a4b5c6d7e8
Revises: e2b3c4d5e6f7
Create Date: 2026-03-27
"""

from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Create enum types (idempotent — safe to re-run if migration was
    #    interrupted after the CREATE TYPE but before CREATE TABLE)
    # -----------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE reporttype AS ENUM ('job', 'user', 'message', 'review');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE reportreason AS ENUM (
                'spam', 'fraud', 'harassment', 'inappropriate_content',
                'fake_account', 'intellectual_property', 'other'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE reportstatus AS ENUM ('pending', 'reviewed', 'resolved', 'dismissed');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)

    # -----------------------------------------------------------------------
    # 2. Create reports table (raw SQL avoids SQLAlchemy re-emitting CREATE TYPE)
    # -----------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            reporter_id UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            report_type reporttype  NOT NULL,
            target_id   UUID        NOT NULL,
            reason      reportreason NOT NULL,
            description TEXT,
            status      reportstatus NOT NULL DEFAULT 'pending',
            reviewed_by UUID        REFERENCES users(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMPTZ,
            admin_note  TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # -----------------------------------------------------------------------
    # 3. Indexes for common query patterns
    # -----------------------------------------------------------------------
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_id          ON reports (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_reporter_id ON reports (reporter_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_report_type ON reports (report_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_target_id   ON reports (target_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_status      ON reports (status)")


def downgrade() -> None:
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_target_id", table_name="reports")
    op.drop_index("ix_reports_report_type", table_name="reports")
    op.drop_index("ix_reports_reporter_id", table_name="reports")
    op.drop_index("ix_reports_id", table_name="reports")

    op.drop_table("reports")

    op.execute("DROP TYPE IF EXISTS reportstatus")
    op.execute("DROP TYPE IF EXISTS reportreason")
    op.execute("DROP TYPE IF EXISTS reporttype")
