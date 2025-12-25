"""Add MFA columns to users

Revision ID: add_mfa_columns
Revises: 1115aee39e63
Create Date: 2025-12-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_mfa_columns'
down_revision: Union[str, None] = '1115aee39e63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add mfa_enabled and totp_secret columns to users table."""
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('totp_secret', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove MFA columns from users table."""
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'mfa_enabled')
