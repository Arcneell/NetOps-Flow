"""Add user_tokens table for refresh token management

Revision ID: 20251225_refresh_tokens
Revises: 1115aee39e63
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251225_refresh_tokens'
down_revision: Union[str, None] = '1115aee39e63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_tokens table for refresh token storage."""
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
    op.create_index(
        'ix_user_tokens_token_hash_not_revoked',
        'user_tokens',
        ['token_hash'],
        unique=False,
        postgresql_where=sa.text('revoked = false')
    )


def downgrade() -> None:
    """Remove user_tokens table."""
    op.drop_index('ix_user_tokens_token_hash_not_revoked', table_name='user_tokens')
    op.drop_table('user_tokens')
