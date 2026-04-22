"""Chat scoping: assigned_staff_id + NULLS NOT DISTINCT unique constraint

Revision ID: d6y7z8a9b0c1
Revises: c5x6y7z8a9b0
Create Date: 2026-04-22

Two schema changes that back PR-C2:

1. conversations.assigned_staff_id — nullable FK users.id used to route
   SUPPORT tickets. Staff only see tickets assigned to them OR
   unassigned (the queue). Before this, any staff user could read every
   support thread on the platform.

2. Tighten the conversations unique constraint. The previous constraint
   was `(participant_one_id, participant_two_id, job_id)`; because
   PostgreSQL treats NULL != NULL by default, a second ORDER-type
   conversation between the same pair + order_id could coexist with
   the first (both rows have job_id=NULL). Replace with a single
   NULLS NOT DISTINCT unique index spanning the full context tuple
   (p1, p2, conversation_type, job_id, order_id). NULLS NOT DISTINCT
   makes NULL values compare equal, so same-type same-context pairs
   collide correctly.

PostgreSQL 16 required for the `NULLS NOT DISTINCT` clause.
"""

import sqlalchemy as sa

from alembic import op

revision = "d6y7z8a9b0c1"
down_revision = "c5x6y7z8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "assigned_staff_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_conversations_assigned_staff_id",
        "conversations",
        ["assigned_staff_id"],
    )

    # Swap the unique constraint. Can't do this with op.create_unique_constraint
    # because we need NULLS NOT DISTINCT — Alembic/SQLAlchemy 2.0 don't yet
    # expose a flag for it, so drop via constraint name and recreate as a
    # unique index with the raw clause.
    op.drop_constraint(
        "uq_conversation_participants_job",
        "conversations",
        type_="unique",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_conversation_participants_context "
        "ON conversations "
        "(participant_one_id, participant_two_id, conversation_type, "
        " job_id, order_id) "
        "NULLS NOT DISTINCT"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_conversation_participants_context")
    op.create_unique_constraint(
        "uq_conversation_participants_job",
        "conversations",
        ["participant_one_id", "participant_two_id", "job_id"],
    )
    op.drop_index(
        "ix_conversations_assigned_staff_id",
        table_name="conversations",
    )
    op.drop_column("conversations", "assigned_staff_id")
