"""schema_drift_fix

Fix schema drift detected by alembic check:
1. Make escrows.funded_at nullable (PENDING escrows don't have it yet)
2. Add unique constraint to gig slug indexes (gig_categories, gig_subcategories, gigs)
3. Add missing id indexes on gig tables (gig_categories, gig_orders, gig_packages, gig_subcategories, gigs)
4. Add missing indexes on users (deleted_at, primary_role, status)

Note: proposals.bid_amount type (Float → Numeric) is fixed in the model only;
the DB already has NUMERIC(12,4) so no DDL change is needed there.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Make escrows.funded_at nullable
    op.alter_column(
        "escrows",
        "funded_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    # 2. Unique constraints on slug columns
    # gig_categories.slug
    op.drop_index("ix_gig_categories_slug", table_name="gig_categories")
    op.create_index("ix_gig_categories_slug", "gig_categories", ["slug"], unique=True)

    # gig_subcategories.slug
    op.drop_index("ix_gig_subcategories_slug", table_name="gig_subcategories")
    op.create_index("ix_gig_subcategories_slug", "gig_subcategories", ["slug"], unique=True)

    # gigs.slug
    op.drop_index("ix_gigs_slug", table_name="gigs")
    op.create_index("ix_gigs_slug", "gigs", ["slug"], unique=True)

    # 3. Missing id indexes on gig tables
    op.create_index("ix_gig_categories_id", "gig_categories", ["id"])
    op.create_index("ix_gig_orders_id", "gig_orders", ["id"])
    op.create_index("ix_gig_packages_id", "gig_packages", ["id"])
    op.create_index("ix_gig_subcategories_id", "gig_subcategories", ["id"])
    op.create_index("ix_gigs_id", "gigs", ["id"])

    # 4. Missing indexes on users
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    op.create_index("ix_users_primary_role", "users", ["primary_role"])
    op.create_index("ix_users_status", "users", ["status"])


def downgrade() -> None:
    # Remove user indexes
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_primary_role", table_name="users")
    op.drop_index("ix_users_deleted_at", table_name="users")

    # Remove gig id indexes
    op.drop_index("ix_gigs_id", table_name="gigs")
    op.drop_index("ix_gig_subcategories_id", table_name="gig_subcategories")
    op.drop_index("ix_gig_packages_id", table_name="gig_packages")
    op.drop_index("ix_gig_orders_id", table_name="gig_orders")
    op.drop_index("ix_gig_categories_id", table_name="gig_categories")

    # Restore non-unique slug indexes
    op.drop_index("ix_gigs_slug", table_name="gigs")
    op.create_index("ix_gigs_slug", "gigs", ["slug"])

    op.drop_index("ix_gig_subcategories_slug", table_name="gig_subcategories")
    op.create_index("ix_gig_subcategories_slug", "gig_subcategories", ["slug"])

    op.drop_index("ix_gig_categories_slug", table_name="gig_categories")
    op.create_index("ix_gig_categories_slug", "gig_categories", ["slug"])

    # Restore escrows.funded_at to NOT NULL
    op.alter_column(
        "escrows",
        "funded_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
