"""support_ticket_lifecycle

Adds status/assignee/resolved_at to the conversations table so SUPPORT
threads can be tracked as tickets (open → in_progress → resolved).

Revision ID: b4x5y6z7a8b9
Revises: a3w4x5y6z7a8
Create Date: 2026-04-21
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b4x5y6z7a8b9"
down_revision = "a3w4x5y6z7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent enum creation.
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE supportticketstatus AS ENUM ('open', 'in_progress', 'resolved'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    op.add_column(
        "conversations",
        sa.Column(
            "support_status",
            postgresql.ENUM(
                "open",
                "in_progress",
                "resolved",
                name="supportticketstatus",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("support_assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "conversations",
        sa.Column("support_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_conversations_support_assignee",
        "conversations",
        "users",
        ["support_assignee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_conversations_support_status",
        "conversations",
        ["support_status"],
    )
    op.create_index(
        "ix_conversations_support_assignee_id",
        "conversations",
        ["support_assignee_id"],
    )

    # Existing SUPPORT threads default to 'open' so they land in the queue.
    op.execute(
        "UPDATE conversations SET support_status = 'open' "
        "WHERE conversation_type = 'support' AND support_status IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_support_assignee_id", table_name="conversations")
    op.drop_index("ix_conversations_support_status", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_support_assignee", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "support_resolved_at")
    op.drop_column("conversations", "support_assignee_id")
    op.drop_column("conversations", "support_status")
    op.execute("DROP TYPE IF EXISTS supportticketstatus")
