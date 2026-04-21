"""Add version column + dispute-release CHECK to escrows

Revision ID: z2u3v4w5x6y7
Revises: y1t2u3v4w5x6
Create Date: 2026-04-21

Two hardening changes on the escrows table:

1. `version` (INTEGER DEFAULT 1 NOT NULL) — used by PaymentService release and
   refund paths for optimistic locking. The release UPDATE now ends with
   `AND version = :expected`, so a stale-read UPDATE from a racing coroutine
   refuses to apply. Sits on top of the existing SELECT FOR UPDATE row lock
   as defence-in-depth.

2. `ck_escrow_no_release_while_disputed` CHECK constraint — a DB-level
   invariant: an escrow in DISPUTED state must not carry a
   release_transaction_id. Service-layer checks already block this path,
   but the CHECK closes the window where a future refactor accidentally
   paths around the service.
"""

import sqlalchemy as sa

from alembic import op

revision = "z2u3v4w5x6y7"
down_revision = "y1t2u3v4w5x6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "escrows",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_check_constraint(
        "ck_escrow_no_release_while_disputed",
        "escrows",
        "NOT (status = 'disputed' AND release_transaction_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_escrow_no_release_while_disputed",
        "escrows",
        type_="check",
    )
    op.drop_column("escrows", "version")
