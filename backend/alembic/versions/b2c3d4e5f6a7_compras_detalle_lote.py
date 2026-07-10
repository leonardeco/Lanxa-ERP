"""compras_detalles: codigo_lote + fecha_vencimiento por renglón

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-10

Capa 3 del módulo de lote+vencimiento (wire-in). El renglón de compra guarda el
lote y su vencimiento para materializarlos como Lote al confirmar. Compatible con
SQLite (batch) y PostgreSQL. Columnas nullable: las compras existentes no cambian.
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("compras_detalles") as batch:
        batch.add_column(sa.Column("codigo_lote", sa.String(length=60), nullable=True))
        batch.add_column(sa.Column("fecha_vencimiento", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("compras_detalles") as batch:
        batch.drop_column("fecha_vencimiento")
        batch.drop_column("codigo_lote")
