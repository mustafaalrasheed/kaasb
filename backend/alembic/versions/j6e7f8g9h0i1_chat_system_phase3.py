"""Chat system phase 3: read receipts + presence last_seen

Revision ID: j6e7f8g9h0i1
Revises: i5d6e7f8g9h0
Create Date: 2026-04-17

* messages.read_at — timestamp set when the recipient opens the conversation.
  Enables ✓ (sent) vs ✓✓ (read) rendering and "Read at 3:45 PM" tooltips.
  Kept alongside the existing ``is_read`` boolean; ``is_read`` stays as the
  authoritative "has been read" flag, ``read_at`` is the moment it happened.
* users.last_seen_at — updated when a user's last WebSocket disconnects.
  Redis holds the live "online now" set; ``last_seen_at`` is the durable
  fallback for showing "Last seen 10 min ago" after the user goes offline.
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "j6e7f8g9h0i1"
down_revision: Union[str, None] = "i5d6e7f8g9h0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_seen_at")
    op.drop_column("messages", "read_at")
