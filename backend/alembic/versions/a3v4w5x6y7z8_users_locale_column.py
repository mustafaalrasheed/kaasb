"""Add locale column on users

Revision ID: a3v4w5x6y7z8
Revises: z2u3v4w5x6y7
Create Date: 2026-04-21

Backs PR-N2 notification localization. Before this migration, notification
title/message were hardcoded in Arabic at every emission site, so English-UI
users saw Arabic text on every push. The service layer now resolves the
right locale per user at emission time using this column; existing users
default to 'ar' (the platform's primary locale).
"""

import sqlalchemy as sa

from alembic import op

revision = "a3v4w5x6y7z8"
down_revision = "z2u3v4w5x6y7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "locale",
            sa.String(length=2),
            nullable=False,
            server_default="ar",
        ),
    )
    op.create_check_constraint(
        "ck_users_locale_supported",
        "users",
        "locale IN ('ar', 'en')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_locale_supported", "users", type_="check")
    op.drop_column("users", "locale")
