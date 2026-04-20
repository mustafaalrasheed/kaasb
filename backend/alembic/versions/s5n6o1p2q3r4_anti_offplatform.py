"""Add violation_logs table for anti off-platform communication (F6)

Revision ID: s5n6o1p2q3r4
Revises: r4m5n6o1p2q3
Create Date: 2026-04-20

Feature 6: Anti Off-Platform Communication
  - New table: violation_logs
  - Enums: violationtype, violationaction
  - users.chat_violations INT (moved from p2k3l4m5n6o1 — already applied there)

Note: chat_violations and chat_suspended_until columns were added to users
in migration p2k3l4m5n6o1 to keep all user column additions together.
This migration only creates the violation_logs table.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "s5n6o1p2q3r4"
down_revision = "r4m5n6o1p2q3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE violationtype AS ENUM ('email', 'phone', 'url', 'external_app');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE violationaction AS ENUM ('warning', 'blocked', 'suspended');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.create_table(
        "violation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "violation_type",
            postgresql.ENUM("email", "phone", "url", "external_app",
                            name="violationtype", create_type=False),
            nullable=False,
        ),
        sa.Column("content_detected", sa.String(500), nullable=False),
        sa.Column(
            "action_taken",
            postgresql.ENUM("warning", "blocked", "suspended",
                            name="violationaction", create_type=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_violation_logs_user_id", "violation_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_violation_logs_user_id", "violation_logs")
    op.drop_table("violation_logs")
    op.execute("DROP TYPE IF EXISTS violationaction")
    op.execute("DROP TYPE IF EXISTS violationtype")
