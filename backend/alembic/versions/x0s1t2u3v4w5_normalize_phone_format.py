"""Normalise Iraqi phone numbers to +9647XXXXXXXXX in users + payment_accounts

Revision ID: x0s1t2u3v4w5
Revises: w9r0s1t2u3v4
Create Date: 2026-04-20

Back-fills existing rows where phones were stored in local format
(``07XXXXXXXXX`` or ``7XXXXXXXXX``) so that OTP lookups (which now receive
``+964...`` from the normalising frontend/backend) find the right user.

Idempotent: already-normalised rows are left alone; non-Iraqi numbers
starting with ``+`` are untouched.
"""

from alembic import op

revision = "x0s1t2u3v4w5"
down_revision = "w9r0s1t2u3v4"
branch_labels = None
depends_on = None


_NORMALIZE_SQL = """
UPDATE {table}
SET {col} = CASE
    WHEN {col} ~ '^\\+9647[0-9]{{9}}$' THEN {col}
    WHEN {col} ~ '^9647[0-9]{{9}}$'    THEN '+' || {col}
    WHEN {col} ~ '^009647[0-9]{{9}}$'  THEN '+' || substring({col} from 3)
    WHEN {col} ~ '^07[0-9]{{9}}$'      THEN '+964' || substring({col} from 2)
    WHEN {col} ~ '^7[0-9]{{9}}$'       THEN '+964' || {col}
    ELSE {col}
END
WHERE {col} IS NOT NULL AND {col} <> '';
"""


def upgrade() -> None:
    op.execute(_NORMALIZE_SQL.format(table="users", col="phone"))
    op.execute(_NORMALIZE_SQL.format(table="payment_accounts", col="qi_card_phone"))


def downgrade() -> None:
    # Normalisation is not reversible — downgrade is a no-op on purpose.
    pass
