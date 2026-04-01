"""gig_marketplace

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-03-29 12:00:00.000000

"""

from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── gig_categories ─────────────────────────────────
    op.create_table(
        "gig_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("name_ar", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gig_categories_slug", "gig_categories", ["slug"])

    # ── gig_subcategories ──────────────────────────────
    op.create_table(
        "gig_subcategories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gig_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("name_ar", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gig_subcategories_slug", "gig_subcategories", ["slug"])

    # ── gig status enum ────────────────────────────────
    # PostgreSQL has no "CREATE TYPE IF NOT EXISTS" — use DO block instead
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE gigstatus AS ENUM ('draft','pending_review','active','paused','rejected','archived');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE gigpackagetier AS ENUM ('basic','standard','premium');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE gigorderstatus AS ENUM ('pending','in_progress','delivered','revision_requested','completed','cancelled','disputed');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)

    # ── gigs ───────────────────────────────────────────
    op.create_table(
        "gigs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("freelancer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(150), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gig_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subcategory_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gig_subcategories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("images", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("thumbnail_url", sa.String(500), nullable=True),
        sa.Column("status", postgresql.ENUM("draft", "pending_review", "active", "paused", "rejected", "archived", name="gigstatus", create_type=False), nullable=False, server_default="pending_review"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("orders_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_rating", sa.Numeric(3, 2), nullable=False, server_default="0.00"),
        sa.Column("reviews_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gigs_freelancer_id", "gigs", ["freelancer_id"])
    op.create_index("ix_gigs_slug", "gigs", ["slug"])
    op.create_index("ix_gigs_status", "gigs", ["status"])

    # ── gig_packages ───────────────────────────────────
    op.create_table(
        "gig_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("gig_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gigs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tier", postgresql.ENUM("basic", "standard", "premium", name="gigpackagetier", create_type=False), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=False),
        sa.Column("revisions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("features", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("gig_id", "tier", name="uq_gig_package_tier"),
    )
    op.create_index("ix_gig_packages_gig_id", "gig_packages", ["gig_id"])

    # ── gig_orders ─────────────────────────────────────
    op.create_table(
        "gig_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("gig_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gigs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("gig_packages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("freelancer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "in_progress", "delivered", "revision_requested", "completed", "cancelled", "disputed", name="gigorderstatus", create_type=False), nullable=False, server_default="pending"),
        sa.Column("requirements", sa.Text, nullable=True),
        sa.Column("price_paid", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=False),
        sa.Column("revisions_remaining", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text, nullable=True),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gig_orders_gig_id", "gig_orders", ["gig_id"])
    op.create_index("ix_gig_orders_client_id", "gig_orders", ["client_id"])
    op.create_index("ix_gig_orders_freelancer_id", "gig_orders", ["freelancer_id"])
    op.create_index("ix_gig_orders_status", "gig_orders", ["status"])

    # ── Seed: Iraqi market categories (skip if already seeded) ──────────
    op.execute("""
        INSERT INTO gig_categories (id, name_en, name_ar, slug, icon, sort_order)
        SELECT gen_random_uuid(), name_en, name_ar, slug, icon, sort_order FROM (VALUES
            ('Design & Creative',   'التصميم والإبداع',         'design',       'Palette',       1),
            ('Programming & Tech',  'البرمجة والتقنية',          'programming',  'Code2',         2),
            ('Writing & Content',   'الكتابة والمحتوى',          'writing',      'FileText',      3),
            ('Video & Animation',   'الفيديو والرسوم المتحركة',   'video',        'Video',         4),
            ('Digital Marketing',   'التسويق الرقمي',            'marketing',    'TrendingUp',    5),
            ('Business',            'الأعمال',                   'business',     'Briefcase',     6),
            ('Audio & Music',       'الصوت والموسيقى',           'audio',        'Music',         7),
            ('Education',           'التعليم',                   'education',    'GraduationCap', 8)
        ) AS v(name_en, name_ar, slug, icon, sort_order)
        WHERE NOT EXISTS (SELECT 1 FROM gig_categories WHERE gig_categories.slug = v.slug)
    """)


def downgrade() -> None:
    op.drop_table("gig_orders")
    op.drop_table("gig_packages")
    op.drop_table("gigs")
    op.drop_table("gig_subcategories")
    op.drop_table("gig_categories")
    op.execute("DROP TYPE IF EXISTS gigorderstatus")
    op.execute("DROP TYPE IF EXISTS gigpackagetier")
    op.execute("DROP TYPE IF EXISTS gigstatus")
