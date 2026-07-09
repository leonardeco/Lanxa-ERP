"""lotes + vencimiento: flag controla_lote, tabla lotes, kardex.lote_id

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-07-09

Capa 1 del módulo de trazabilidad por lote. Compatible con SQLite (batch) y
PostgreSQL. No migra stock existente: los productos arrancan con controla_lote=False.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("producto_id", sa.Integer(), nullable=False),
        sa.Column("codigo_lote", sa.String(length=60), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
        sa.Column("cantidad_actual", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("cantidad_inicial", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("costo_unitario", sa.Numeric(18, 2), nullable=True),
        sa.Column("origen", sa.String(length=40), nullable=True),
        sa.Column("fecha_ingreso", sa.DateTime(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["producto_id"], ["productos.id"]),
        sa.UniqueConstraint("producto_id", "codigo_lote", name="uq_lote_producto_codigo"),
    )
    op.create_index("ix_lotes_producto_id", "lotes", ["producto_id"])
    op.create_index("ix_lotes_fecha_vencimiento", "lotes", ["fecha_vencimiento"])

    with op.batch_alter_table("productos") as batch:
        batch.add_column(sa.Column(
            "controla_lote", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("movimientos_inventario") as batch:
        batch.add_column(sa.Column("lote_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_mov_lote", "lotes", ["lote_id"], ["id"])
        batch.create_index("ix_movimientos_inventario_lote_id", ["lote_id"])


def downgrade() -> None:
    with op.batch_alter_table("movimientos_inventario") as batch:
        batch.drop_index("ix_movimientos_inventario_lote_id")
        batch.drop_constraint("fk_mov_lote", type_="foreignkey")
        batch.drop_column("lote_id")

    with op.batch_alter_table("productos") as batch:
        batch.drop_column("controla_lote")

    op.drop_index("ix_lotes_fecha_vencimiento", table_name="lotes")
    op.drop_index("ix_lotes_producto_id", table_name="lotes")
    op.drop_table("lotes")
