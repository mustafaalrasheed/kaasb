"""legal_compliance

Adds tables and indexes for Prompt 11 — Legal & Compliance:

1. reports table — content moderation reports (jobs, users, messages, reviews)
2. Enum types: report_type, report_reason, report_status

Revision ID: f3a4b5c6d7e8
Revises: e2b3c4d5e6f7
Create Date: 2026-03-27
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Create enum types
    # -----------------------------------------------------------------------
    op.execute(
        "CREATE TYPE reporttype AS ENUM ('job', 'user', 'message', 'review')"
    )
    op.execute(
        "CREATE TYPE reportreason AS ENUM ("
        "'spam', 'fraud', 'harassment', 'inappropriate_content', "
        "'fake_account', 'intellectual_property', 'other')"
    )
    op.execute(
        "CREATE TYPE reportstatus AS ENUM ('pending', 'reviewed', 'resolved', 'dismissed')"
    )

    # -----------------------------------------------------------------------
    # 2. Create reports table
    # -----------------------------------------------------------------------
    op.create_table(
        "reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_type",
            sa.Enum("job", "user", "message", "review", name="reporttype"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.Enum(
                "spam", "fraud", "harassment", "inappropriate_content",
                "fake_account", "intellectual_property", "other",
                name="reportreason",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "reviewed", "resolved", "dismissed", name="reportstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )

    # -----------------------------------------------------------------------
    # 3. Indexes for common query patterns
    # -----------------------------------------------------------------------
    op.create_index("ix_reports_id", "reports", ["id"])
    op.create_index("ix_reports_reporter_id", "reports", ["reporter_id"])
    op.create_index("ix_reports_report_type", "reports", ["report_type"])
    op.create_index("ix_reports_target_id", "reports", ["target_id"])
    op.create_index("ix_reports_status", "reports", ["status"])


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
