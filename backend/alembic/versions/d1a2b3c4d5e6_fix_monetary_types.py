"""fix_monetary_types

CRITICAL: Convert Float monetary columns to Numeric for exact decimal arithmetic.
Float (double precision / float8) accumulates rounding errors in financial
calculations. E.g., 0.1 + 0.2 = 0.30000000000000004 in float — unacceptable
for escrow, payout, and transaction amounts.

Also adds missing database-level CHECK constraints that exist in the SQLAlchemy
models but were absent from the initial migration (they were never written to
the DB, meaning business rules were enforced at the application layer only).

⚠  PRODUCTION LOCK WARNING:
   ALTER COLUMN TYPE acquires ACCESS EXCLUSIVE lock on the table.
   Each table will be briefly unavailable during the type conversion.
   Estimated time at <100K rows: ~1-3 seconds per table.
   Run during off-peak hours or a maintenance window.

   Pre-migration checklist:
     1. Run scripts/pre-migration-checklist.sh
     2. Verify a fresh backup exists (< 1 hour old)
     3. Schedule during off-peak traffic window

Revision ID: d1a2b3c4d5e6
Revises: c7d4e8f2a901
Create Date: 2026-03-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd1a2b3c4d5e6'
down_revision: Union[str, None] = 'c7d4e8f2a901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─────────────────────────────────────────────────────────────────────────
    # USERS — hourly_rate, total_earnings, total_spent, avg_rating
    # ─────────────────────────────────────────────────────────────────────────
    # Single ALTER TABLE statement = single ACCESS EXCLUSIVE lock acquisition.
    # Multiple column changes in one statement are more efficient than separate ones.
    op.execute("""
        ALTER TABLE users
            ALTER COLUMN hourly_rate    TYPE NUMERIC(8,2)  USING hourly_rate::NUMERIC(8,2),
            ALTER COLUMN total_earnings TYPE NUMERIC(12,4) USING total_earnings::NUMERIC(12,4),
            ALTER COLUMN total_spent    TYPE NUMERIC(12,4) USING total_spent::NUMERIC(12,4),
            ALTER COLUMN avg_rating     TYPE NUMERIC(3,2)  USING avg_rating::NUMERIC(3,2)
    """)

    # ─────────────────────────────────────────────────────────────────────────
    # JOBS — budget_min, budget_max, fixed_price + CHECK constraints
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE jobs
            ALTER COLUMN budget_min  TYPE NUMERIC(12,4) USING budget_min::NUMERIC(12,4),
            ALTER COLUMN budget_max  TYPE NUMERIC(12,4) USING budget_max::NUMERIC(12,4),
            ALTER COLUMN fixed_price TYPE NUMERIC(12,4) USING fixed_price::NUMERIC(12,4)
    """)

    # NOT VALID: adds constraint without a full table scan lock (ShareUpdateExclusiveLock).
    # VALIDATE CONSTRAINT: runs the scan separately, still under ShareUpdateExclusiveLock
    # (not ACCESS EXCLUSIVE), so reads/writes can proceed concurrently.
    op.execute("""
        ALTER TABLE jobs
            ADD CONSTRAINT ck_job_budget_min_positive
                CHECK (budget_min >= 0) NOT VALID,
            ADD CONSTRAINT ck_job_budget_max_positive
                CHECK (budget_max >= 0) NOT VALID,
            ADD CONSTRAINT ck_job_budget_range_valid
                CHECK (budget_max IS NULL OR budget_min IS NULL OR budget_max >= budget_min) NOT VALID,
            ADD CONSTRAINT ck_job_fixed_price_positive
                CHECK (fixed_price IS NULL OR fixed_price > 0) NOT VALID
    """)
    op.execute("ALTER TABLE jobs VALIDATE CONSTRAINT ck_job_budget_min_positive")
    op.execute("ALTER TABLE jobs VALIDATE CONSTRAINT ck_job_budget_max_positive")
    op.execute("ALTER TABLE jobs VALIDATE CONSTRAINT ck_job_budget_range_valid")
    op.execute("ALTER TABLE jobs VALIDATE CONSTRAINT ck_job_fixed_price_positive")

    # ─────────────────────────────────────────────────────────────────────────
    # PROPOSALS — bid_amount + CHECK constraint
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE proposals
            ALTER COLUMN bid_amount TYPE NUMERIC(12,4) USING bid_amount::NUMERIC(12,4)
    """)
    op.execute("""
        ALTER TABLE proposals
            ADD CONSTRAINT ck_proposal_bid_positive
                CHECK (bid_amount > 0) NOT VALID
    """)
    op.execute("ALTER TABLE proposals VALIDATE CONSTRAINT ck_proposal_bid_positive")

    # ─────────────────────────────────────────────────────────────────────────
    # CONTRACTS — total_amount, amount_paid + CHECK constraints
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE contracts
            ALTER COLUMN total_amount TYPE NUMERIC(12,4) USING total_amount::NUMERIC(12,4),
            ALTER COLUMN amount_paid  TYPE NUMERIC(12,4) USING amount_paid::NUMERIC(12,4)
    """)
    op.execute("""
        ALTER TABLE contracts
            ADD CONSTRAINT ck_contract_total_amount_positive
                CHECK (total_amount > 0) NOT VALID,
            ADD CONSTRAINT ck_contract_amount_paid_non_negative
                CHECK (amount_paid >= 0) NOT VALID,
            ADD CONSTRAINT ck_contract_amount_paid_le_total
                CHECK (amount_paid <= total_amount) NOT VALID
    """)
    op.execute("ALTER TABLE contracts VALIDATE CONSTRAINT ck_contract_total_amount_positive")
    op.execute("ALTER TABLE contracts VALIDATE CONSTRAINT ck_contract_amount_paid_non_negative")
    op.execute("ALTER TABLE contracts VALIDATE CONSTRAINT ck_contract_amount_paid_le_total")

    # ─────────────────────────────────────────────────────────────────────────
    # MILESTONES — amount + CHECK constraint
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE milestones
            ALTER COLUMN amount TYPE NUMERIC(12,4) USING amount::NUMERIC(12,4)
    """)
    op.execute("""
        ALTER TABLE milestones
            ADD CONSTRAINT ck_milestone_amount_positive
                CHECK (amount > 0) NOT VALID
    """)
    op.execute("ALTER TABLE milestones VALIDATE CONSTRAINT ck_milestone_amount_positive")

    # ─────────────────────────────────────────────────────────────────────────
    # TRANSACTIONS — amount, platform_fee, net_amount + CHECK constraints
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE transactions
            ALTER COLUMN amount       TYPE NUMERIC(12,4) USING amount::NUMERIC(12,4),
            ALTER COLUMN platform_fee TYPE NUMERIC(12,4) USING platform_fee::NUMERIC(12,4),
            ALTER COLUMN net_amount   TYPE NUMERIC(12,4) USING net_amount::NUMERIC(12,4)
    """)
    op.execute("""
        ALTER TABLE transactions
            ADD CONSTRAINT ck_transaction_amount_positive
                CHECK (amount > 0) NOT VALID,
            ADD CONSTRAINT ck_transaction_fee_non_negative
                CHECK (platform_fee >= 0) NOT VALID,
            ADD CONSTRAINT ck_transaction_net_positive
                CHECK (net_amount > 0) NOT VALID
    """)
    op.execute("ALTER TABLE transactions VALIDATE CONSTRAINT ck_transaction_amount_positive")
    op.execute("ALTER TABLE transactions VALIDATE CONSTRAINT ck_transaction_fee_non_negative")
    op.execute("ALTER TABLE transactions VALIDATE CONSTRAINT ck_transaction_net_positive")

    # ─────────────────────────────────────────────────────────────────────────
    # ESCROWS — amount, platform_fee, freelancer_amount + CHECK constraints
    # ─────────────────────────────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE escrows
            ALTER COLUMN amount            TYPE NUMERIC(12,4) USING amount::NUMERIC(12,4),
            ALTER COLUMN platform_fee      TYPE NUMERIC(12,4) USING platform_fee::NUMERIC(12,4),
            ALTER COLUMN freelancer_amount TYPE NUMERIC(12,4) USING freelancer_amount::NUMERIC(12,4)
    """)
    op.execute("""
        ALTER TABLE escrows
            ADD CONSTRAINT ck_escrow_amount_positive
                CHECK (amount > 0) NOT VALID,
            ADD CONSTRAINT ck_escrow_fee_non_negative
                CHECK (platform_fee >= 0) NOT VALID,
            ADD CONSTRAINT ck_escrow_freelancer_amount_positive
                CHECK (freelancer_amount > 0) NOT VALID,
            ADD CONSTRAINT ck_escrow_freelancer_le_total
                CHECK (freelancer_amount <= amount) NOT VALID
    """)
    op.execute("ALTER TABLE escrows VALIDATE CONSTRAINT ck_escrow_amount_positive")
    op.execute("ALTER TABLE escrows VALIDATE CONSTRAINT ck_escrow_fee_non_negative")
    op.execute("ALTER TABLE escrows VALIDATE CONSTRAINT ck_escrow_freelancer_amount_positive")
    op.execute("ALTER TABLE escrows VALIDATE CONSTRAINT ck_escrow_freelancer_le_total")


def downgrade() -> None:
    # ── Remove CHECK constraints ─────────────────────────────────────────────
    op.execute("ALTER TABLE escrows DROP CONSTRAINT IF EXISTS ck_escrow_freelancer_le_total")
    op.execute("ALTER TABLE escrows DROP CONSTRAINT IF EXISTS ck_escrow_freelancer_amount_positive")
    op.execute("ALTER TABLE escrows DROP CONSTRAINT IF EXISTS ck_escrow_fee_non_negative")
    op.execute("ALTER TABLE escrows DROP CONSTRAINT IF EXISTS ck_escrow_amount_positive")
    op.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS ck_transaction_net_positive")
    op.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS ck_transaction_fee_non_negative")
    op.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS ck_transaction_amount_positive")
    op.execute("ALTER TABLE milestones DROP CONSTRAINT IF EXISTS ck_milestone_amount_positive")
    op.execute("ALTER TABLE contracts DROP CONSTRAINT IF EXISTS ck_contract_amount_paid_le_total")
    op.execute("ALTER TABLE contracts DROP CONSTRAINT IF EXISTS ck_contract_amount_paid_non_negative")
    op.execute("ALTER TABLE contracts DROP CONSTRAINT IF EXISTS ck_contract_total_amount_positive")
    op.execute("ALTER TABLE proposals DROP CONSTRAINT IF EXISTS ck_proposal_bid_positive")
    op.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS ck_job_fixed_price_positive")
    op.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS ck_job_budget_range_valid")
    op.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS ck_job_budget_max_positive")
    op.execute("ALTER TABLE jobs DROP CONSTRAINT IF EXISTS ck_job_budget_min_positive")

    # ── Revert Numeric → Float ────────────────────────────────────────────────
    # ⚠ WARNING: This loses decimal precision. Values are preserved as
    # best-effort double precision. Do NOT downgrade on production financial data.
    op.execute("""
        ALTER TABLE escrows
            ALTER COLUMN freelancer_amount TYPE FLOAT8 USING freelancer_amount::FLOAT8,
            ALTER COLUMN platform_fee      TYPE FLOAT8 USING platform_fee::FLOAT8,
            ALTER COLUMN amount            TYPE FLOAT8 USING amount::FLOAT8
    """)
    op.execute("""
        ALTER TABLE transactions
            ALTER COLUMN net_amount   TYPE FLOAT8 USING net_amount::FLOAT8,
            ALTER COLUMN platform_fee TYPE FLOAT8 USING platform_fee::FLOAT8,
            ALTER COLUMN amount       TYPE FLOAT8 USING amount::FLOAT8
    """)
    op.execute("""
        ALTER TABLE milestones
            ALTER COLUMN amount TYPE FLOAT8 USING amount::FLOAT8
    """)
    op.execute("""
        ALTER TABLE contracts
            ALTER COLUMN amount_paid  TYPE FLOAT8 USING amount_paid::FLOAT8,
            ALTER COLUMN total_amount TYPE FLOAT8 USING total_amount::FLOAT8
    """)
    op.execute("""
        ALTER TABLE proposals
            ALTER COLUMN bid_amount TYPE FLOAT8 USING bid_amount::FLOAT8
    """)
    op.execute("""
        ALTER TABLE jobs
            ALTER COLUMN fixed_price TYPE FLOAT8 USING fixed_price::FLOAT8,
            ALTER COLUMN budget_max  TYPE FLOAT8 USING budget_max::FLOAT8,
            ALTER COLUMN budget_min  TYPE FLOAT8 USING budget_min::FLOAT8
    """)
    op.execute("""
        ALTER TABLE users
            ALTER COLUMN avg_rating     TYPE FLOAT8 USING avg_rating::FLOAT8,
            ALTER COLUMN total_spent    TYPE FLOAT8 USING total_spent::FLOAT8,
            ALTER COLUMN total_earnings TYPE FLOAT8 USING total_earnings::FLOAT8,
            ALTER COLUMN hourly_rate    TYPE FLOAT8 USING hourly_rate::FLOAT8
    """)
