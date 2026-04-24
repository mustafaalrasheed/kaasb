"""Add terms_accepted_at + terms_version to users — persist legal consent

Revision ID: f8a9b0c1d2e3
Revises: e7z8a9b0c1d2
Create Date: 2026-04-25

Per signup-audit 2026-04-25 F1: the Terms of Service + Privacy Policy +
Acceptable Use checkbox on the register form was UI-only. Nothing posted
to the backend, nothing stored. If a user later disputed a clause, Kaasb
could not prove they accepted it at signup. Consumer-protection statutes
typically require a record of consent at the moment of contract
formation.

Both columns are nullable because existing users predate the field and
we have no retroactive evidence of consent. Any user whose
``terms_accepted_at`` is NULL is assumed pre-feature (on the first
"Terms updated — please re-accept" prompt we'll flip them).
"""

import sqlalchemy as sa
from alembic import op

revision = "f8a9b0c1d2e3"
down_revision = "e7z8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("terms_version", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "terms_version")
    op.drop_column("users", "terms_accepted_at")
