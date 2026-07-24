"""ventas_diarias: modulo de ventas contraentrega (Peru/Ecuador, Run 6)

Revision ID: a9b8c7d6e5f4
Revises: c6d7e8f9a0b1
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "a9b8c7d6e5f4"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ventas_diarias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("asesor", sa.String(length=200), nullable=True),
        sa.Column("guia", sa.String(length=50), nullable=True),
        sa.Column("codigo_guia", sa.String(length=20), nullable=True),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum("PENDIENTE", "ENTREGADO", "EN_DESTINO", "DEVOLUCION",
                    name="estadoventadiaria"),
            nullable=False,
        ),
        sa.Column("forma_pago", sa.String(length=100), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ventas_diarias_tenant_id", "ventas_diarias", ["tenant_id"])
    op.create_index("ix_ventas_diarias_guia", "ventas_diarias", ["guia"])

    op.create_table(
        "ventas_diarias_detalles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("venta_diaria_id", sa.Integer(), nullable=False),
        sa.Column("producto_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Numeric(12, 2), nullable=False),
        sa.Column("venta", sa.Numeric(18, 2), nullable=True),
        sa.Column("abono_1", sa.Numeric(18, 2), nullable=True),
        sa.Column("abono_2", sa.Numeric(18, 2), nullable=True),
        sa.Column("saldo", sa.Numeric(18, 2), nullable=False),
        sa.Column("pesos_c", sa.Numeric(18, 2), nullable=True),
        sa.Column("valor_flete", sa.Numeric(18, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["venta_diaria_id"], ["ventas_diarias.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["productos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ventas_diarias_detalles_tenant_id", "ventas_diarias_detalles", ["tenant_id"])
    op.create_index(
        "ix_ventas_diarias_detalles_venta_diaria_id",
        "ventas_diarias_detalles", ["venta_diaria_id"])

    op.create_table(
        "pagos_sueltos_diarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cliente_texto", sa.String(length=300), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("revisado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pagos_sueltos_diarios_tenant_id", "pagos_sueltos_diarios", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("pagos_sueltos_diarios")
    op.drop_index(
        "ix_ventas_diarias_detalles_venta_diaria_id", table_name="ventas_diarias_detalles")
    op.drop_index("ix_ventas_diarias_detalles_tenant_id", table_name="ventas_diarias_detalles")
    op.drop_table("ventas_diarias_detalles")
    op.drop_index("ix_ventas_diarias_guia", table_name="ventas_diarias")
    op.drop_index("ix_ventas_diarias_tenant_id", table_name="ventas_diarias")
    op.drop_table("ventas_diarias")
    sa.Enum(name="estadoventadiaria").drop(op.get_bind(), checkfirst=True)
