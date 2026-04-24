"""Add service_order_id to reviews + relax contract_id — dual review path

Revision ID: e7z8a9b0c1d2
Revises: d6y7z8a9b0c1
Create Date: 2026-04-25

Per reviews-audit 2026-04-25 F1 (launch blocker): ``ReviewService.submit_review``
hard-required ``contract_id``, so service-order completions had no review path.
Gig-style sellers who completed dozens of orders showed 0 reviews on their
profile because only contract reviews ever landed in the aggregate.

Changes:
  1. ``reviews.contract_id`` → nullable (existing rows keep their FK).
  2. ``reviews.service_order_id`` → new nullable FK to ``service_orders(id)``.
  3. CHECK constraint: exactly one of (contract_id, service_order_id) is set
     — a review always points at exactly one transaction, never both.
  4. Drop legacy ``uq_one_review_per_contract_per_user`` — it had NOT-NULL
     semantics baked in via the non-nullable column. Replace with two partial
     unique indexes so the "one review per reviewer per transaction" rule
     applies per-side regardless of review type.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e7z8a9b0c1d2"
down_revision = "d6y7z8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("reviews", "contract_id", nullable=True)

    op.add_column(
        "reviews",
        sa.Column(
            "service_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_orders.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_reviews_service_order_id",
        "reviews",
        ["service_order_id"],
    )

    op.create_check_constraint(
        "ck_reviews_exactly_one_target",
        "reviews",
        "(contract_id IS NOT NULL AND service_order_id IS NULL) "
        "OR (contract_id IS NULL AND service_order_id IS NOT NULL)",
    )

    op.drop_constraint(
        "uq_one_review_per_contract_per_user",
        "reviews",
        type_="unique",
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_reviews_contract_reviewer "
        "ON reviews (contract_id, reviewer_id) "
        "WHERE contract_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_reviews_order_reviewer "
        "ON reviews (service_order_id, reviewer_id) "
        "WHERE service_order_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_reviews_order_reviewer")
    op.execute("DROP INDEX IF EXISTS uq_reviews_contract_reviewer")
    op.create_unique_constraint(
        "uq_one_review_per_contract_per_user",
        "reviews",
        ["contract_id", "reviewer_id"],
    )

    op.drop_constraint(
        "ck_reviews_exactly_one_target",
        "reviews",
        type_="check",
    )

    op.drop_index("ix_reviews_service_order_id", table_name="reviews")
    op.drop_column("reviews", "service_order_id")

    op.alter_column("reviews", "contract_id", nullable=False)
