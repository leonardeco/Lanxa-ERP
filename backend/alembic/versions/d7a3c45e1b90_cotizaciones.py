"""cotizaciones: COT-#### con flujo Borrador→Enviada→Aprobada/Rechazada→Convertida

Revision ID: d7a3c45e1b90
Revises: c3e9a17f5d02
Create Date: 2026-07-05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd7a3c45e1b90'
down_revision: Union[str, None] = 'c3e9a17f5d02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cotizaciones',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('numero', sa.String(length=20), nullable=False),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('vigencia_dias', sa.Integer(), nullable=False),
        sa.Column('fecha_vencimiento', sa.Date(), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('vendedor', sa.String(length=200), nullable=True),
        sa.Column('subtotal', sa.Numeric(18, 2), nullable=False),
        sa.Column('descuento_total', sa.Numeric(18, 2), nullable=False),
        sa.Column('base_gravable', sa.Numeric(18, 2), nullable=False),
        sa.Column('iva_total', sa.Numeric(18, 2), nullable=False),
        sa.Column('total', sa.Numeric(18, 2), nullable=False),
        sa.Column('estado', sa.Enum(
            'BORRADOR', 'ENVIADA', 'APROBADA', 'RECHAZADA', 'CONVERTIDA',
            name='estadocotizacion'), nullable=False),
        sa.Column('motivo_rechazo', sa.String(length=300), nullable=True),
        sa.Column('venta_id', sa.Integer(), nullable=True),
        sa.Column('observaciones', sa.Text(), nullable=True),
        sa.Column('usuario_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id']),
        sa.ForeignKeyConstraint(['venta_id'], ['ventas_documentos.id']),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cotizaciones_numero', 'cotizaciones', ['numero'], unique=True)
    op.create_index('ix_cotizaciones_venta_id', 'cotizaciones', ['venta_id'])

    op.create_table(
        'cotizaciones_detalles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cotizacion_id', sa.Integer(), nullable=False),
        sa.Column('producto_id', sa.Integer(), nullable=False),
        sa.Column('cantidad', sa.Numeric(12, 2), nullable=False),
        sa.Column('precio_unitario', sa.Numeric(18, 2), nullable=False),
        sa.Column('descuento_porcentaje', sa.Numeric(5, 2), nullable=False),
        sa.Column('subtotal_linea', sa.Numeric(18, 2), nullable=False),
        sa.Column('iva_porcentaje', sa.Numeric(5, 2), nullable=False),
        sa.Column('iva_valor', sa.Numeric(18, 2), nullable=False),
        sa.Column('total_linea', sa.Numeric(18, 2), nullable=False),
        sa.Column('notas', sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(['cotizacion_id'], ['cotizaciones.id']),
        sa.ForeignKeyConstraint(['producto_id'], ['productos.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('cotizaciones_detalles')
    op.drop_index('ix_cotizaciones_venta_id', table_name='cotizaciones')
    op.drop_index('ix_cotizaciones_numero', table_name='cotizaciones')
    op.drop_table('cotizaciones')
