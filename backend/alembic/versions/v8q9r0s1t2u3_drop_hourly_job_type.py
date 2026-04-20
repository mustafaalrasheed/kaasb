"""Drop hourly from JobType enum — Kaasb is fixed-price only

Revision ID: v8q9r0s1t2u3
Revises: u7p8q9r0s1t2
Create Date: 2026-04-20

- Convert any existing jobs with job_type='hourly' to 'fixed' (and copy budget_min
  into fixed_price if fixed_price is NULL, since hourly jobs never filled it).
- Recreate the jobtype enum with only 'fixed' as a valid value.
"""

import sqlalchemy as sa

from alembic import op

revision = "v8q9r0s1t2u3"
down_revision = "u7p8q9r0s1t2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Any hourly job → fixed. If fixed_price is NULL, take budget_min (or 5 as floor).
    op.execute(
        """
        UPDATE jobs
        SET fixed_price = COALESCE(fixed_price, budget_min, 5)
        WHERE job_type = 'hourly'
        """
    )
    op.execute("UPDATE jobs SET job_type = 'fixed' WHERE job_type = 'hourly'")

    # 2. Swap enum: rename old → _old, create new with only 'fixed', cast column, drop old.
    op.execute("ALTER TYPE jobtype RENAME TO jobtype_old")
    op.execute("CREATE TYPE jobtype AS ENUM ('fixed')")
    op.execute(
        "ALTER TABLE jobs ALTER COLUMN job_type TYPE jobtype "
        "USING job_type::text::jobtype"
    )
    op.execute("DROP TYPE jobtype_old")


def downgrade() -> None:
    # Recreate the old enum with both values. Existing data stays 'fixed' — no way
    # to restore which jobs used to be hourly.
    op.execute("ALTER TYPE jobtype RENAME TO jobtype_old")
    op.execute("CREATE TYPE jobtype AS ENUM ('fixed', 'hourly')")
    op.execute(
        "ALTER TABLE jobs ALTER COLUMN job_type TYPE jobtype "
        "USING job_type::text::jobtype"
    )
    op.execute("DROP TYPE jobtype_old")
    # Silence unused-import warning when only op.execute is used.
    _ = sa
