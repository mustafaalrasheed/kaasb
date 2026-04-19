"""Escrow: replace full unique constraints with partial unique indexes

Revision ID: l8g9h0i1j2k3
Revises: k7f8g9h0i1j2
Create Date: 2026-04-19

Problem:
  The current UNIQUE(milestone_id) and UNIQUE(gig_order_id) constraints on the
  escrows table prevent a client from retrying payment after a failure or
  cancellation.  When a payment fails, the escrow is marked REFUNDED, but the
  unique constraint still blocks creating a new PENDING escrow for the same
  milestone or gig order.

Fix:
  Replace the full unique constraints with partial unique indexes that only
  enforce uniqueness when the escrow is in an active state (pending or funded).
  Released, refunded, and disputed escrows are excluded from the uniqueness check,
  so a new PENDING escrow can be created after a failed payment.
"""

from alembic import op

revision = "l8g9h0i1j2k3"
down_revision = "k7f8g9h0i1j2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Normalize escrowstatus enum values from uppercase (initial migration legacy)
    # to lowercase (Python model standard). Idempotent: only renames if uppercase
    # label exists, so safe to run on both fresh CI databases and production.
    for old, new in [
        ("PENDING", "pending"),
        ("FUNDED", "funded"),
        ("RELEASED", "released"),
        ("REFUNDED", "refunded"),
        ("DISPUTED", "disputed"),
    ]:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_enum e
                    JOIN pg_type t ON e.enumtypid = t.oid
                    WHERE t.typname = 'escrowstatus' AND e.enumlabel = '{old}'
                ) THEN
                    ALTER TYPE escrowstatus RENAME VALUE '{old}' TO '{new}';
                END IF;
            END $$;
            """
        )

    # Drop existing full unique constraints (may not exist on all environments)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_escrow_milestone' AND conrelid = 'escrows'::regclass
            ) THEN
                ALTER TABLE escrows DROP CONSTRAINT uq_escrow_milestone;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_escrow_gig_order' AND conrelid = 'escrows'::regclass
            ) THEN
                ALTER TABLE escrows DROP CONSTRAINT uq_escrow_gig_order;
            END IF;
        END $$;
        """
    )

    # Create partial unique indexes — only enforce uniqueness for active escrows.
    # RELEASED, REFUNDED, DISPUTED escrows do not block new PENDING escrows.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_escrow_milestone_active
        ON escrows (milestone_id)
        WHERE milestone_id IS NOT NULL
          AND status IN ('pending', 'funded')
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_escrow_gig_order_active
        ON escrows (gig_order_id)
        WHERE gig_order_id IS NOT NULL
          AND status IN ('pending', 'funded')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_escrow_milestone_active")
    op.execute("DROP INDEX IF EXISTS uq_escrow_gig_order_active")

    op.create_unique_constraint("uq_escrow_milestone", "escrows", ["milestone_id"])
    op.create_unique_constraint("uq_escrow_gig_order", "escrows", ["gig_order_id"])
