"""pagos: columna anulado para reverso de abonos

Revision ID: 8a1c2f0d4b21
Revises: 72f7b9fae762
Create Date: 2026-07-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8a1c2f0d4b21'
down_revision: Union[str, None] = '72f7b9fae762'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('anulado', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.drop_column('anulado')
