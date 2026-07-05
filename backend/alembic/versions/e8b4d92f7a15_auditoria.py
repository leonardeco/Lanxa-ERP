"""auditoria: log de cambios en datos maestros y acciones administrativas

Revision ID: e8b4d92f7a15
Revises: d7a3c45e1b90
Create Date: 2026-07-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e8b4d92f7a15'
down_revision: Union[str, None] = 'd7a3c45e1b90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auditoria',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('fecha', sa.DateTime(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('usuario_email', sa.String(length=150), nullable=True),
        sa.Column('accion', sa.String(length=30), nullable=False),
        sa.Column('entidad', sa.String(length=50), nullable=False),
        sa.Column('entidad_id', sa.Integer(), nullable=True),
        sa.Column('descripcion', sa.String(length=300), nullable=False),
        sa.Column('cambios', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_auditoria_fecha', 'auditoria', ['fecha'])
    op.create_index('ix_auditoria_accion', 'auditoria', ['accion'])
    op.create_index('ix_auditoria_entidad', 'auditoria', ['entidad'])


def downgrade() -> None:
    op.drop_index('ix_auditoria_entidad', table_name='auditoria')
    op.drop_index('ix_auditoria_accion', table_name='auditoria')
    op.drop_index('ix_auditoria_fecha', table_name='auditoria')
    op.drop_table('auditoria')
