"""Add is_support flag on users for limited-privilege support staff

Revision ID: w9r0s1t2u3v4
Revises: v8q9r0s1t2u3
Create Date: 2026-04-20

Introduces an is_support boolean on users. Support staff can read admin views
and handle support/dispute triage but cannot release money or change user state
— those remain gated on is_superuser.
"""

import sqlalchemy as sa

from alembic import op

revision = "w9r0s1t2u3v4"
down_revision = "v8q9r0s1t2u3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_support",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_support")
