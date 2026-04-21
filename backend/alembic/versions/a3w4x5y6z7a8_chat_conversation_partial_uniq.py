"""Replace conversations unique constraint with three partial unique indexes

Revision ID: a3w4x5y6z7a8
Revises: z2v3w4x5y6z7
Create Date: 2026-04-21

The original constraint ``uq_conversation_participants_job`` covered
``(participant_one_id, participant_two_id, job_id)``. Postgres treats NULL as
distinct in unique constraints, so two "bare" conversations with the same
participant pair and NULL ``job_id`` / NULL ``order_id`` were allowed through,
which lets concurrent ``start_conversation`` calls create duplicate threads.

Replacement: three partial unique indexes, one per conversation shape.

  * ``uq_conv_bare``      — one per pair when neither job nor order is set
                            (covers plain USER threads and user↔admin SUPPORT threads).
  * ``uq_conv_by_job``    — one per (pair, job).
  * ``uq_conv_by_order``  — one per (pair, order).

If duplicates already exist this migration will FAIL at index creation; that
is intentional — it forces a human to investigate and merge rather than
silently clobber conversation history.
"""

from alembic import op

revision = "a3w4x5y6z7a8"
down_revision = "z2v3w4x5y6z7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_conversation_participants_job", "conversations", type_="unique",
    )

    op.execute("""
        CREATE UNIQUE INDEX uq_conv_bare
        ON conversations (participant_one_id, participant_two_id)
        WHERE job_id IS NULL AND order_id IS NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_conv_by_job
        ON conversations (participant_one_id, participant_two_id, job_id)
        WHERE job_id IS NOT NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_conv_by_order
        ON conversations (participant_one_id, participant_two_id, order_id)
        WHERE order_id IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_conv_by_order")
    op.execute("DROP INDEX IF EXISTS uq_conv_by_job")
    op.execute("DROP INDEX IF EXISTS uq_conv_bare")
    op.create_unique_constraint(
        "uq_conversation_participants_job",
        "conversations",
        ["participant_one_id", "participant_two_id", "job_id"],
    )
