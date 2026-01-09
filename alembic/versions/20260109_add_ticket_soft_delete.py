"""Add soft delete columns to tickets table

Revision ID: 20260109_soft_delete
Revises: 20251225_refresh_tokens
Create Date: 2026-01-09

Adds is_deleted, deleted_at, and deleted_by_id columns to enable soft delete
functionality for tickets. This allows tickets to be marked as deleted without
permanently removing them from the database.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '20260109_soft_delete'
down_revision: Union[str, None] = '20251225_refresh_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add soft delete columns to tickets table."""
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if tickets table exists
    existing_tables = inspector.get_table_names()
    if 'tickets' not in existing_tables:
        # Table doesn't exist yet - SQLAlchemy create_all will handle this
        return

    # Check existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('tickets')]

    # Add is_deleted column if not exists
    if 'is_deleted' not in existing_columns:
        op.add_column('tickets', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
        op.create_index('ix_tickets_is_deleted', 'tickets', ['is_deleted'])

    # Add deleted_at column if not exists
    if 'deleted_at' not in existing_columns:
        op.add_column('tickets', sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # Add deleted_by_id column if not exists
    if 'deleted_by_id' not in existing_columns:
        op.add_column('tickets', sa.Column(
            'deleted_by_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        ))


def downgrade() -> None:
    """Remove soft delete columns from tickets table."""
    conn = op.get_bind()
    inspector = inspect(conn)

    existing_tables = inspector.get_table_names()
    if 'tickets' not in existing_tables:
        return

    existing_columns = [col['name'] for col in inspector.get_columns('tickets')]

    # Drop columns in reverse order
    if 'deleted_by_id' in existing_columns:
        op.drop_column('tickets', 'deleted_by_id')

    if 'deleted_at' in existing_columns:
        op.drop_column('tickets', 'deleted_at')

    if 'is_deleted' in existing_columns:
        try:
            op.drop_index('ix_tickets_is_deleted', table_name='tickets')
        except Exception:
            pass
        op.drop_column('tickets', 'is_deleted')
