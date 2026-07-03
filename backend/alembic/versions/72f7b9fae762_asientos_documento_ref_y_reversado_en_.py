"""asientos: documento_ref y reversado en asientos_contables

Revision ID: 72f7b9fae762
Revises: 99c028642b89
Create Date: 2026-07-02

Nota: el autogenerate detectó además drift de nulabilidad/tipos entre las BD
creadas con los modelos legacy (create_all pre-tipado) y los modelos 2.0.
Ese drift se dejó FUERA a propósito — apretar NOT NULL contra datos reales
requiere su propia migración con backfill revisado. Aquí solo va lo que el
motor de asientos necesita.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '72f7b9fae762'
down_revision: Union[str, None] = '99c028642b89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('asientos_contables', schema=None) as batch_op:
        batch_op.add_column(sa.Column('documento_ref', sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column('reversado', sa.Boolean(), nullable=False, server_default=sa.text('0'))
        )
        batch_op.create_index(
            batch_op.f('ix_asientos_contables_documento_ref'), ['documento_ref'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('asientos_contables', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_asientos_contables_documento_ref'))
        batch_op.drop_column('reversado')
        batch_op.drop_column('documento_ref')
