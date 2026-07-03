"""devoluciones: notas credito de venta y devoluciones a proveedor

Revision ID: c3e9a17f5d02
Revises: 8a1c2f0d4b21
Create Date: 2026-07-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3e9a17f5d02'
down_revision: Union[str, None] = '8a1c2f0d4b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'devoluciones_venta',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('numero', sa.String(length=20), nullable=False),
        sa.Column('venta_id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('motivo', sa.String(length=300), nullable=False),
        sa.Column('subtotal', sa.Numeric(18, 2), nullable=False),
        sa.Column('iva_total', sa.Numeric(18, 2), nullable=False),
        sa.Column('total', sa.Numeric(18, 2), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['venta_id'], ['ventas_documentos.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_devoluciones_venta_numero', 'devoluciones_venta', ['numero'], unique=True)
    op.create_index('ix_devoluciones_venta_venta_id', 'devoluciones_venta', ['venta_id'])

    op.create_table(
        'devoluciones_venta_detalles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('devolucion_id', sa.Integer(), nullable=False),
        sa.Column('venta_detalle_id', sa.Integer(), nullable=False),
        sa.Column('producto_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Numeric(12, 3), nullable=False),
        sa.Column('precio_unitario', sa.Numeric(18, 2), nullable=False),
        sa.Column('subtotal_linea', sa.Numeric(18, 2), nullable=False),
        sa.Column('iva_valor', sa.Numeric(18, 2), nullable=False),
        sa.Column('total_linea', sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(['devolucion_id'], ['devoluciones_venta.id']),
        sa.ForeignKeyConstraint(['venta_detalle_id'], ['ventas_detalles.id']),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'devoluciones_compra',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('numero', sa.String(length=20), nullable=False),
        sa.Column('compra_id', sa.Integer(), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('motivo', sa.String(length=300), nullable=False),
        sa.Column('subtotal', sa.Numeric(18, 2), nullable=False),
        sa.Column('iva_total', sa.Numeric(18, 2), nullable=False),
        sa.Column('total', sa.Numeric(18, 2), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['compra_id'], ['compras_documentos.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_devoluciones_compra_numero', 'devoluciones_compra', ['numero'], unique=True)
    op.create_index('ix_devoluciones_compra_compra_id', 'devoluciones_compra', ['compra_id'])

    op.create_table(
        'devoluciones_compra_detalles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('devolucion_id', sa.Integer(), nullable=False),
        sa.Column('compra_detalle_id', sa.Integer(), nullable=False),
        sa.Column('producto_id', sa.Integer(), nullable=True),
        sa.Column('descripcion', sa.String(length=300), nullable=False),
        sa.Column('cantidad', sa.Numeric(12, 3), nullable=False),
        sa.Column('precio_unitario', sa.Numeric(18, 2), nullable=False),
        sa.Column('subtotal_linea', sa.Numeric(18, 2), nullable=False),
        sa.Column('iva_valor', sa.Numeric(18, 2), nullable=False),
        sa.Column('total_linea', sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(['devolucion_id'], ['devoluciones_compra.id']),
        sa.ForeignKeyConstraint(['compra_detalle_id'], ['compras_detalles.id']),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('devoluciones_compra_detalles')
    op.drop_index('ix_devoluciones_compra_compra_id', table_name='devoluciones_compra')
    op.drop_index('ix_devoluciones_compra_numero', table_name='devoluciones_compra')
    op.drop_table('devoluciones_compra')
    op.drop_table('devoluciones_venta_detalles')
    op.drop_index('ix_devoluciones_venta_venta_id', table_name='devoluciones_venta')
    op.drop_index('ix_devoluciones_venta_numero', table_name='devoluciones_venta')
    op.drop_table('devoluciones_venta')
