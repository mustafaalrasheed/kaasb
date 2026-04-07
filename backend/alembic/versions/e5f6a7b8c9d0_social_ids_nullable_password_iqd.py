"""social_ids_nullable_password_iqd

Add google_id/facebook_id to users for social login deduplication.
Make hashed_password nullable for social-only accounts.
Change currency default from USD to IQD on transactions and escrows.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users: add social login ID columns ---
    op.add_column("users", sa.Column("google_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("facebook_id", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])
    op.create_unique_constraint("uq_users_facebook_id", "users", ["facebook_id"])

    # --- users: make hashed_password nullable for social-only accounts ---
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=True,
    )

    # --- transactions: change currency default from USD to IQD ---
    op.alter_column(
        "transactions",
        "currency",
        existing_type=sa.String(3),
        server_default="IQD",
        existing_nullable=False,
    )

    # --- escrows: change currency default from USD to IQD ---
    op.alter_column(
        "escrows",
        "currency",
        existing_type=sa.String(3),
        server_default="IQD",
        existing_nullable=False,
    )


def downgrade() -> None:
    # --- escrows: revert currency default ---
    op.alter_column(
        "escrows",
        "currency",
        existing_type=sa.String(3),
        server_default="USD",
        existing_nullable=False,
    )

    # --- transactions: revert currency default ---
    op.alter_column(
        "transactions",
        "currency",
        existing_type=sa.String(3),
        server_default="USD",
        existing_nullable=False,
    )

    # --- users: revert hashed_password to NOT NULL ---
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=False,
    )

    # --- users: remove social login columns ---
    op.drop_constraint("uq_users_facebook_id", "users", type_="unique")
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
    op.drop_column("users", "facebook_id")
    op.drop_column("users", "google_id")
