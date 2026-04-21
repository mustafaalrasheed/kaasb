"""Rename "gig" → "service" across the marketplace schema.

Revision ID: z2v3w4x5y6z7
Revises: y1u2v3w4x5y6
Create Date: 2026-04-21

The English word "gig" doesn't fit the Iraqi market — locals don't recognise it,
and the Arabic UI already uses خدمة (khidma / service). This migration renames
the entity everywhere so EN and AR finally agree.

Scope:
- 6 tables: gigs, gig_packages, gig_orders, gig_categories, gig_subcategories,
  gig_order_deliveries → service_*
- 3 enum types: gigstatus, gigorderstatus, gigpackagetier → service*
- Column renames: gig_id → service_id (packages, orders, buyer_request_offers);
  gig_order_id → service_order_id (escrows)
- notificationtype enum values: gig_* → service_*
- notifications.link_type values: "gig" / "gig_order" → "service" / "service_order"
- Indexes and unique constraints renamed for consistency.

All renames are reversible. The downgrade path is provided but best-effort:
dropping and re-creating enum values is destructive if new rows have been
inserted with the renamed values.
"""

from alembic import op

revision = "z2v3w4x5y6z7"
down_revision = "y1u2v3w4x5y6"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------------------------
def upgrade() -> None:
    # ── 1. Rename enum types ────────────────────────────────────────────────
    op.execute("ALTER TYPE gigstatus RENAME TO servicestatus")
    op.execute("ALTER TYPE gigorderstatus RENAME TO serviceorderstatus")
    op.execute("ALTER TYPE gigpackagetier RENAME TO servicepackagetier")

    # ── 2. Rename notificationtype enum values ─────────────────────────────
    # Postgres 10+ supports ALTER TYPE ... RENAME VALUE ... TO ...
    op.execute(
        "ALTER TYPE notificationtype RENAME VALUE 'gig_approved' TO 'service_approved'"
    )
    op.execute(
        "ALTER TYPE notificationtype RENAME VALUE 'gig_rejected' TO 'service_rejected'"
    )
    op.execute(
        "ALTER TYPE notificationtype RENAME VALUE 'gig_submitted' TO 'service_submitted'"
    )
    op.execute(
        "ALTER TYPE notificationtype RENAME VALUE 'gig_needs_revision' "
        "TO 'service_needs_revision'"
    )

    # ── 2b. Rename adminauditaction enum values ────────────────────────────
    op.execute(
        "ALTER TYPE adminauditaction RENAME VALUE 'gig_approved' "
        "TO 'service_approved'"
    )
    op.execute(
        "ALTER TYPE adminauditaction RENAME VALUE 'gig_rejected' "
        "TO 'service_rejected'"
    )

    # ── 3. Rename tables ────────────────────────────────────────────────────
    # Parents first so FKs continue to resolve by name through the rename.
    op.rename_table("gig_categories", "service_categories")
    op.rename_table("gig_subcategories", "service_subcategories")
    op.rename_table("gigs", "services")
    op.rename_table("gig_packages", "service_packages")
    op.rename_table("gig_orders", "service_orders")
    op.rename_table("gig_order_deliveries", "service_order_deliveries")

    # ── 4. Rename FK columns ───────────────────────────────────────────────
    op.alter_column("service_packages", "gig_id", new_column_name="service_id")
    op.alter_column("service_orders", "gig_id", new_column_name="service_id")
    op.alter_column("buyer_request_offers", "gig_id", new_column_name="service_id")
    op.alter_column("escrows", "gig_order_id", new_column_name="service_order_id")

    # ── 5. Rename unique constraint on service_packages ────────────────────
    op.execute(
        "ALTER TABLE service_packages "
        "RENAME CONSTRAINT uq_gig_package_tier TO uq_service_package_tier"
    )

    # ── 6. Rename indexes (keep names in sync with table + column names) ───
    # Ignored if the index doesn't exist — some were created automatically by
    # `index=True` on mapped_column and Postgres auto-generates names that
    # already match the new table via the rename_table. The explicitly-named
    # ones from the original migration are renamed here.
    _rename_index_if_exists(
        "ix_gigs_freelancer_id", "ix_services_freelancer_id"
    )
    _rename_index_if_exists("ix_gigs_slug", "ix_services_slug")
    _rename_index_if_exists("ix_gigs_status", "ix_services_status")
    _rename_index_if_exists(
        "ix_gig_categories_slug", "ix_service_categories_slug"
    )
    _rename_index_if_exists(
        "ix_gig_subcategories_slug", "ix_service_subcategories_slug"
    )
    _rename_index_if_exists(
        "ix_gig_packages_gig_id", "ix_service_packages_service_id"
    )
    _rename_index_if_exists(
        "ix_gig_orders_gig_id", "ix_service_orders_service_id"
    )
    _rename_index_if_exists(
        "ix_gig_orders_client_id", "ix_service_orders_client_id"
    )
    _rename_index_if_exists(
        "ix_gig_orders_freelancer_id", "ix_service_orders_freelancer_id"
    )
    _rename_index_if_exists(
        "ix_gig_orders_status", "ix_service_orders_status"
    )

    # ── 7. Update in-row notification link_type values ─────────────────────
    op.execute(
        "UPDATE notifications SET link_type = 'service' WHERE link_type = 'gig'"
    )
    op.execute(
        "UPDATE notifications SET link_type = 'service_order' "
        "WHERE link_type = 'gig_order'"
    )


# ---------------------------------------------------------------------------
# DOWNGRADE
# ---------------------------------------------------------------------------
def downgrade() -> None:
    # Reverse order of upgrade.
    op.execute(
        "UPDATE notifications SET link_type = 'gig_order' "
        "WHERE link_type = 'service_order'"
    )
    op.execute(
        "UPDATE notifications SET link_type = 'gig' WHERE link_type = 'service'"
    )

    _rename_index_if_exists(
        "ix_service_orders_status", "ix_gig_orders_status"
    )
    _rename_index_if_exists(
        "ix_service_orders_freelancer_id", "ix_gig_orders_freelancer_id"
    )
    _rename_index_if_exists(
        "ix_service_orders_client_id", "ix_gig_orders_client_id"
    )
    _rename_index_if_exists(
        "ix_service_orders_service_id", "ix_gig_orders_gig_id"
    )
    _rename_index_if_exists(
        "ix_service_packages_service_id", "ix_gig_packages_gig_id"
    )
    _rename_index_if_exists(
        "ix_service_subcategories_slug", "ix_gig_subcategories_slug"
    )
    _rename_index_if_exists(
        "ix_service_categories_slug", "ix_gig_categories_slug"
    )
    _rename_index_if_exists("ix_services_status", "ix_gigs_status")
    _rename_index_if_exists("ix_services_slug", "ix_gigs_slug")
    _rename_index_if_exists(
        "ix_services_freelancer_id", "ix_gigs_freelancer_id"
    )

    op.execute(
        "ALTER TABLE service_packages "
        "RENAME CONSTRAINT uq_service_package_tier TO uq_gig_package_tier"
    )

    op.alter_column("escrows", "service_order_id", new_column_name="gig_order_id")
    op.alter_column(
        "buyer_request_offers", "service_id", new_column_name="gig_id"
    )
    op.alter_column("service_orders", "service_id", new_column_name="gig_id")
    op.alter_column("service_packages", "service_id", new_column_name="gig_id")

    op.rename_table("service_order_deliveries", "gig_order_deliveries")
    op.rename_table("service_orders", "gig_orders")
    op.rename_table("service_packages", "gig_packages")
    op.rename_table("services", "gigs")
    op.rename_table("service_subcategories", "gig_subcategories")
    op.rename_table("service_categories", "gig_categories")

    op.execute(
        "ALTER TYPE notificationtype RENAME VALUE 'service_needs_revision' "
        "TO 'gig_needs_revision'"
    )
    op.execute(
        "ALTER TYPE notificationtype RENAME VALUE 'service_submitted' TO 'gig_submitted'"
    )
    op.execute(
        "ALTER TYPE notificationtype RENAME VALUE 'service_rejected' TO 'gig_rejected'"
    )
    op.execute(
        "ALTER TYPE notificationtype RENAME VALUE 'service_approved' TO 'gig_approved'"
    )

    # Reverse adminauditaction enum renames
    op.execute(
        "ALTER TYPE adminauditaction RENAME VALUE 'service_rejected' "
        "TO 'gig_rejected'"
    )
    op.execute(
        "ALTER TYPE adminauditaction RENAME VALUE 'service_approved' "
        "TO 'gig_approved'"
    )

    op.execute("ALTER TYPE servicepackagetier RENAME TO gigpackagetier")
    op.execute("ALTER TYPE serviceorderstatus RENAME TO gigorderstatus")
    op.execute("ALTER TYPE servicestatus RENAME TO gigstatus")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _rename_index_if_exists(old: str, new: str) -> None:
    """Rename an index only when it exists — some indexes were auto-created by
    SQLAlchemy's ``index=True`` and may have been renamed implicitly via
    rename_table on newer Postgres, while others were explicitly named in the
    original migration."""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_class WHERE relname = '{old}') THEN
                ALTER INDEX {old} RENAME TO {new};
            END IF;
        END $$;
        """
    )
