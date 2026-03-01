"""add jobs table

Revision ID: f32778932130
Revises:
Create Date: 2026-02-19 11:50:23.561450
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = 'f32778932130'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define ENUM types (create_type=False means use existing types)
    jobstatus = postgresql.ENUM('draft', 'open', 'in_progress', 'completed', 'cancelled', 'closed', name='jobstatus', create_type=False)
    jobtype = postgresql.ENUM('fixed', 'hourly', name='jobtype', create_type=False)
    experiencelevel = postgresql.ENUM('entry', 'intermediate', 'expert', name='experiencelevel', create_type=False)
    jobduration = postgresql.ENUM('less_than_1_week', '1_to_4_weeks', '1_to_3_months', '3_to_6_months', 'more_than_6_months', name='jobduration', create_type=False)

    # Create jobs table (ENUMs already exist in database)
    op.create_table('jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('job_type', jobtype, nullable=False),
        sa.Column('budget_min', sa.Float(), nullable=True),
        sa.Column('budget_max', sa.Float(), nullable=True),
        sa.Column('fixed_price', sa.Float(), nullable=True),
        sa.Column('skills_required', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('experience_level', experiencelevel, nullable=True),
        sa.Column('duration', jobduration, nullable=True),
        sa.Column('status', jobstatus, nullable=False),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('freelancer_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('proposal_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['freelancer_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(op.f('ix_jobs_title'), 'jobs', ['title'])
    op.create_index(op.f('ix_jobs_category'), 'jobs', ['category'])
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'])
    op.create_index(op.f('ix_jobs_client_id'), 'jobs', ['client_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_jobs_client_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_category'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_title'), table_name='jobs')

    # Drop table
    op.drop_table('jobs')

    # Drop ENUM types
    sa.Enum(name='jobduration').drop(op.get_bind())
    sa.Enum(name='experiencelevel').drop(op.get_bind())
    sa.Enum(name='jobtype').drop(op.get_bind())
    sa.Enum(name='jobstatus').drop(op.get_bind())
