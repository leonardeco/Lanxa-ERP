"""tenants: columna dominio para login por email-domain (#37)

Revision ID: 4e24b843eccd
Revises: 3deee189e9bd
Create Date: 2026-08-03

Añade `tenants.dominio` (parte del email después del @, minúsculas, único).
Backfill inmediato para los dos tenants conocidos:
  - codigo='superozono' -> superozonoglobal.com
  - codigo='peru'       -> superozonoperu.com  [CONFIRMAR con el negocio]

IMPORTANTE: si el dominio de Perú no es superozonoperu.com, ejecutar:
    UPDATE tenants SET dominio = 'dominio-real.com' WHERE codigo = 'peru';
y notificar al usuario auxiliar.peru@... que su email de login cambia.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e24b843eccd'
down_revision: Union[str, None] = '3deee189e9bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Añade columna dominio y hace backfill de los tenants existentes."""
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.add_column(sa.Column('dominio', sa.String(length=200), nullable=True))
        batch_op.create_index('ix_tenants_dominio', ['dominio'], unique=True)

    # Backfill: tenant Colombia y Perú (si existe)
    op.execute(
        "UPDATE tenants SET dominio = 'superozonoglobal.com' WHERE codigo = 'superozono'"
    )
    op.execute(
        "UPDATE tenants SET dominio = 'superozonoperu.com' WHERE codigo = 'peru'"
    )


def downgrade() -> None:
    """Elimina columna dominio."""
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.drop_index('ix_tenants_dominio')
        batch_op.drop_column('dominio')
