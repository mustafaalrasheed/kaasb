"""Add session metadata to refresh tokens

Revision ID: h4c5d6e7f8g9
Revises: g3b4c5d6e7f8
Create Date: 2026-04-15

Adds ip_address and last_used_at columns to refresh_tokens so the user
can view and revoke active sessions from the settings page.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "h4c5d6e7f8g9"
down_revision: Union[str, None] = "g3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("refresh_tokens", sa.Column("ip_address", sa.String(length=45), nullable=True))
    op.add_column("refresh_tokens", sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("refresh_tokens", "last_used_at")
    op.drop_column("refresh_tokens", "ip_address")
