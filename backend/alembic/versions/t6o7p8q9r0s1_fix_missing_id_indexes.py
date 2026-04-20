"""Fix missing id indexes and disputes.order_id unique index

Revision ID: t6o7p8q9r0s1
Revises: s5n6o1p2q3r4
Create Date: 2026-04-20

Adds id indexes that BaseModel declares (index=True on primary key)
but were omitted from the initial table migrations, and fixes
ix_disputes_order_id to be unique (matching the UniqueConstraint on
Dispute.order_id).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "t6o7p8q9r0s1"
down_revision = "s5n6o1p2q3r4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # buyer_requests
    op.create_index("ix_buyer_requests_id", "buyer_requests", ["id"])
    # buyer_request_offers
    op.create_index("ix_buyer_request_offers_id", "buyer_request_offers", ["id"])
    # disputes: recreate order_id index as unique + add id index
    op.drop_index("ix_disputes_order_id", table_name="disputes")
    op.create_index("ix_disputes_order_id", "disputes", ["order_id"], unique=True)
    op.create_index("ix_disputes_id", "disputes", ["id"])
    # gig_order_deliveries
    op.create_index("ix_gig_order_deliveries_id", "gig_order_deliveries", ["id"])
    # violation_logs
    op.create_index("ix_violation_logs_id", "violation_logs", ["id"])


def downgrade() -> None:
    op.drop_index("ix_violation_logs_id", table_name="violation_logs")
    op.drop_index("ix_gig_order_deliveries_id", table_name="gig_order_deliveries")
    op.drop_index("ix_disputes_id", table_name="disputes")
    op.drop_index("ix_disputes_order_id", table_name="disputes")
    op.create_index("ix_disputes_order_id", "disputes", ["order_id"], unique=False)
    op.drop_index("ix_buyer_request_offers_id", table_name="buyer_request_offers")
    op.drop_index("ix_buyer_requests_id", table_name="buyer_requests")
