"""auditoria: columna ip del request (#32)

Revision ID: f1a2b3c4d5e6
Revises: e8b4d92f7a15
Create Date: 2026-07-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e8b4d92f7a15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('auditoria', sa.Column('ip', sa.String(length=45), nullable=True))


def downgrade() -> None:
    op.drop_column('auditoria', 'ip')
