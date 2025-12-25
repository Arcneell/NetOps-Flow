"""Add user_tokens table for refresh token management

Revision ID: 20251225_refresh_tokens
Revises: 1115aee39e63
Create Date: 2025-12-25

Note: This migration is designed to work with SQLAlchemy's create_all()
which handles table creation after migrations run. The user_tokens table
is defined in models.py and will be created by create_all() if it doesn't
exist. This migration serves as documentation and for environments that
rely purely on Alembic.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '20251225_refresh_tokens'
down_revision: Union[str, None] = '1115aee39e63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_tokens table for refresh token storage.

    This migration checks if tables exist before creating them,
    as SQLAlchemy's create_all() may handle this after migrations.
    """
    # Get connection and inspector
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Skip if table already exists (created by SQLAlchemy create_all)
    if 'user_tokens' in existing_tables:
        return

    # Check if users table exists (required for foreign key)
    if 'users' not in existing_tables:
        # Users table doesn't exist yet - SQLAlchemy create_all will handle this
        # Just return and let create_all() create all tables with proper dependencies
        return

    # Create the table if users exists but user_tokens doesn't
    op.create_table(
        'user_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('token_hash', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('revoked', sa.Boolean(), default=False),
        sa.Column('device_info', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
    )

    # Create index for efficient token lookup
    try:
        op.create_index(
            'ix_user_tokens_token_hash_not_revoked',
            'user_tokens',
            ['token_hash'],
            unique=False,
            postgresql_where=sa.text('revoked = false')
        )
    except Exception:
        # Index may already exist or partial index not supported
        pass


def downgrade() -> None:
    """Remove user_tokens table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'user_tokens' not in existing_tables:
        return

    try:
        op.drop_index('ix_user_tokens_token_hash_not_revoked', table_name='user_tokens')
    except Exception:
        pass

    op.drop_table('user_tokens')
