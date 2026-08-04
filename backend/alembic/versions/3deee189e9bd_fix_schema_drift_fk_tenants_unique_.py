"""fix-schema-drift: fk-tenants + unique-constraints-compuestos (#40)

Revision ID: 3deee189e9bd
Revises: a9b8c7d6e5f4
Create Date: 2026-08-03 23:18:23.671205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3deee189e9bd'
down_revision: Union[str, None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tablas que solo necesitan FK a tenants (sin cambios de índice)
_FK_ONLY_TABLES = [
    'asientos_contables',
    'auditoria',
    'compras_detalles',
    'cotizaciones_detalles',
    'devoluciones_compra_detalles',
    'devoluciones_venta_detalles',
    'document_sequences',
    'lotes',
    'movimientos_asiento',
    'periodos_contables',
    'refresh_tokens',
    'saldos_iniciales',
    'usuarios',
    'ventas_detalles',
]


def upgrade() -> None:
    """Upgrade schema."""

    # ── FK-only tables ───────────────────────────────────────────────────────
    for table in _FK_ONLY_TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.create_foreign_key(
                f'fk_{table}_tenant_id', 'tenants', ['tenant_id'], ['id'],
                ondelete='RESTRICT',
            )

    # ── centros_costo ────────────────────────────────────────────────────────
    with op.batch_alter_table('centros_costo', schema=None) as batch_op:
        batch_op.drop_index('uq_cc_tenant_codigo')
        batch_op.drop_index('ix_centros_costo_codigo')
        batch_op.create_index('ix_centros_costo_codigo', ['codigo'], unique=True)
        batch_op.create_foreign_key(
            'fk_centros_costo_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── clientes ─────────────────────────────────────────────────────────────
    with op.batch_alter_table('clientes', schema=None) as batch_op:
        batch_op.drop_index('uq_clientes_tenant_nit')
        batch_op.create_unique_constraint('uq_clientes_tenant_nit', ['tenant_id', 'nit_cc'])
        batch_op.create_foreign_key(
            'fk_clientes_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── compras_documentos ───────────────────────────────────────────────────
    with op.batch_alter_table('compras_documentos', schema=None) as batch_op:
        batch_op.drop_index('uq_compras_tenant_numero')
        batch_op.drop_index('ix_compras_documentos_numero')
        batch_op.create_index('ix_compras_documentos_numero', ['numero'], unique=True)
        batch_op.create_foreign_key(
            'fk_compras_documentos_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── cotizaciones ─────────────────────────────────────────────────────────
    with op.batch_alter_table('cotizaciones', schema=None) as batch_op:
        batch_op.drop_index('uq_cotizaciones_tenant_numero')
        batch_op.drop_index('ix_cotizaciones_numero')
        batch_op.create_index('ix_cotizaciones_numero', ['numero'], unique=True)
        batch_op.create_foreign_key(
            'fk_cotizaciones_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── cuentas_por_cobrar ───────────────────────────────────────────────────
    with op.batch_alter_table('cuentas_por_cobrar', schema=None) as batch_op:
        batch_op.drop_index('ix_cuentas_por_cobrar_numero_factura')
        batch_op.drop_index('uq_cxc_tenant_factura')
        batch_op.create_foreign_key(
            'fk_cuentas_por_cobrar_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── cuentas_por_pagar ────────────────────────────────────────────────────
    with op.batch_alter_table('cuentas_por_pagar', schema=None) as batch_op:
        batch_op.drop_index('ix_cuentas_por_pagar_numero_documento')
        batch_op.drop_index('uq_cxp_tenant_documento')
        batch_op.create_foreign_key(
            'fk_cuentas_por_pagar_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── devoluciones_compra ──────────────────────────────────────────────────
    with op.batch_alter_table('devoluciones_compra', schema=None) as batch_op:
        batch_op.drop_index('uq_dev_compra_tenant_numero')
        batch_op.drop_index('ix_devoluciones_compra_numero')
        batch_op.create_index('ix_devoluciones_compra_numero', ['numero'], unique=True)
        batch_op.create_foreign_key(
            'fk_devoluciones_compra_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── devoluciones_venta ───────────────────────────────────────────────────
    with op.batch_alter_table('devoluciones_venta', schema=None) as batch_op:
        batch_op.drop_index('uq_dev_venta_tenant_numero')
        batch_op.drop_index('ix_devoluciones_venta_numero')
        batch_op.create_index('ix_devoluciones_venta_numero', ['numero'], unique=True)
        batch_op.create_foreign_key(
            'fk_devoluciones_venta_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── movimientos_inventario ───────────────────────────────────────────────
    with op.batch_alter_table('movimientos_inventario', schema=None) as batch_op:
        batch_op.alter_column(
            'origen',
            existing_type=sa.VARCHAR(length=14),
            type_=sa.Enum(
                'COMPRA', 'VENTA', 'AJUSTE_MANUAL', 'REVERSO_COMPRA',
                'REVERSO_VENTA', 'DEVOLUCION_VENTA', 'DEVOLUCION_COMPRA',
                name='origenmovimiento',
            ),
            existing_nullable=False,
        )
        batch_op.create_foreign_key(
            'fk_movimientos_inventario_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── pagos ────────────────────────────────────────────────────────────────
    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.drop_index('uq_pagos_tenant_numero')
        batch_op.drop_index('ix_pagos_numero_comprobante')
        batch_op.create_index('ix_pagos_numero_comprobante', ['numero_comprobante'], unique=True)
        batch_op.create_foreign_key(
            'fk_pagos_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── parametros_nomina ────────────────────────────────────────────────────
    with op.batch_alter_table('parametros_nomina', schema=None) as batch_op:
        batch_op.drop_index('ix_parametros_nomina_concepto')
        batch_op.drop_index('uq_param_nom_tenant_concepto')
        batch_op.create_foreign_key(
            'fk_parametros_nomina_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── parametros_tributarios ───────────────────────────────────────────────
    with op.batch_alter_table('parametros_tributarios', schema=None) as batch_op:
        batch_op.drop_index('ix_parametros_tributarios_concepto')
        batch_op.drop_index('uq_param_trib_tenant_concepto')
        batch_op.create_foreign_key(
            'fk_parametros_tributarios_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── plan_cuentas ─────────────────────────────────────────────────────────
    with op.batch_alter_table('plan_cuentas', schema=None) as batch_op:
        batch_op.drop_index('uq_puc_tenant_codigo')
        batch_op.drop_index('ix_plan_cuentas_codigo_puc')
        batch_op.create_index('ix_plan_cuentas_codigo_puc', ['codigo_puc'], unique=True)
        batch_op.create_foreign_key(
            'fk_plan_cuentas_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── productos ────────────────────────────────────────────────────────────
    with op.batch_alter_table('productos', schema=None) as batch_op:
        batch_op.drop_index('uq_productos_tenant_sku')
        batch_op.create_unique_constraint('uq_productos_tenant_sku', ['tenant_id', 'sku'])
        batch_op.create_foreign_key(
            'fk_productos_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── proveedores ──────────────────────────────────────────────────────────
    with op.batch_alter_table('proveedores', schema=None) as batch_op:
        batch_op.drop_index('uq_proveedores_tenant_nit')
        batch_op.create_unique_constraint('uq_proveedores_tenant_nit', ['tenant_id', 'nit_cc'])
        batch_op.create_foreign_key(
            'fk_proveedores_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── tenants (unique en codigo) ───────────────────────────────────────────
    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.drop_index('ix_tenants_codigo')
        batch_op.create_index('ix_tenants_codigo', ['codigo'], unique=True)

    # ── terceros ─────────────────────────────────────────────────────────────
    with op.batch_alter_table('terceros', schema=None) as batch_op:
        batch_op.drop_index('uq_terceros_tenant_nit')
        batch_op.drop_index('ix_terceros_nit_cc')
        batch_op.create_index('ix_terceros_nit_cc', ['nit_cc'], unique=True)
        batch_op.create_foreign_key(
            'fk_terceros_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )

    # ── ventas_documentos ────────────────────────────────────────────────────
    with op.batch_alter_table('ventas_documentos', schema=None) as batch_op:
        batch_op.drop_index('uq_ventas_tenant_numero')
        batch_op.create_foreign_key(
            'fk_ventas_documentos_tenant_id', 'tenants', ['tenant_id'], ['id'],
            ondelete='RESTRICT',
        )


def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table('ventas_documentos', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ventas_documentos_tenant_id', type_='foreignkey')
        batch_op.create_index('uq_ventas_tenant_numero', ['tenant_id', 'numero'], unique=True)

    with op.batch_alter_table('terceros', schema=None) as batch_op:
        batch_op.drop_constraint('fk_terceros_tenant_id', type_='foreignkey')
        batch_op.drop_index('ix_terceros_nit_cc')
        batch_op.create_index('ix_terceros_nit_cc', ['nit_cc'], unique=False)
        batch_op.create_index('uq_terceros_tenant_nit', ['tenant_id', 'nit_cc'], unique=True)

    with op.batch_alter_table('tenants', schema=None) as batch_op:
        batch_op.drop_index('ix_tenants_codigo')
        batch_op.create_index('ix_tenants_codigo', ['codigo'], unique=False)

    with op.batch_alter_table('proveedores', schema=None) as batch_op:
        batch_op.drop_constraint('fk_proveedores_tenant_id', type_='foreignkey')
        batch_op.drop_constraint('uq_proveedores_tenant_nit', type_='unique')
        batch_op.create_index('uq_proveedores_tenant_nit', ['tenant_id', 'nit_cc'], unique=True)

    with op.batch_alter_table('productos', schema=None) as batch_op:
        batch_op.drop_constraint('fk_productos_tenant_id', type_='foreignkey')
        batch_op.drop_constraint('uq_productos_tenant_sku', type_='unique')
        batch_op.create_index('uq_productos_tenant_sku', ['tenant_id', 'sku'], unique=True)

    with op.batch_alter_table('plan_cuentas', schema=None) as batch_op:
        batch_op.drop_constraint('fk_plan_cuentas_tenant_id', type_='foreignkey')
        batch_op.drop_index('ix_plan_cuentas_codigo_puc')
        batch_op.create_index('ix_plan_cuentas_codigo_puc', ['codigo_puc'], unique=False)
        batch_op.create_index('uq_puc_tenant_codigo', ['tenant_id', 'codigo_puc'], unique=True)

    with op.batch_alter_table('parametros_tributarios', schema=None) as batch_op:
        batch_op.drop_constraint('fk_parametros_tributarios_tenant_id', type_='foreignkey')
        batch_op.create_index('uq_param_trib_tenant_concepto', ['tenant_id', 'concepto'], unique=True)
        batch_op.create_index('ix_parametros_tributarios_concepto', ['concepto'], unique=False)

    with op.batch_alter_table('parametros_nomina', schema=None) as batch_op:
        batch_op.drop_constraint('fk_parametros_nomina_tenant_id', type_='foreignkey')
        batch_op.create_index('uq_param_nom_tenant_concepto', ['tenant_id', 'concepto'], unique=True)
        batch_op.create_index('ix_parametros_nomina_concepto', ['concepto'], unique=False)

    with op.batch_alter_table('pagos', schema=None) as batch_op:
        batch_op.drop_constraint('fk_pagos_tenant_id', type_='foreignkey')
        batch_op.drop_index('ix_pagos_numero_comprobante')
        batch_op.create_index('ix_pagos_numero_comprobante', ['numero_comprobante'], unique=False)
        batch_op.create_index('uq_pagos_tenant_numero', ['tenant_id', 'numero_comprobante'], unique=True)

    with op.batch_alter_table('movimientos_inventario', schema=None) as batch_op:
        batch_op.drop_constraint('fk_movimientos_inventario_tenant_id', type_='foreignkey')
        batch_op.alter_column(
            'origen',
            existing_type=sa.Enum(
                'COMPRA', 'VENTA', 'AJUSTE_MANUAL', 'REVERSO_COMPRA',
                'REVERSO_VENTA', 'DEVOLUCION_VENTA', 'DEVOLUCION_COMPRA',
                name='origenmovimiento',
            ),
            type_=sa.VARCHAR(length=14),
            existing_nullable=False,
        )

    with op.batch_alter_table('devoluciones_venta', schema=None) as batch_op:
        batch_op.drop_constraint('fk_devoluciones_venta_tenant_id', type_='foreignkey')
        batch_op.drop_index('ix_devoluciones_venta_numero')
        batch_op.create_index('ix_devoluciones_venta_numero', ['numero'], unique=False)
        batch_op.create_index('uq_dev_venta_tenant_numero', ['tenant_id', 'numero'], unique=True)

    with op.batch_alter_table('devoluciones_compra', schema=None) as batch_op:
        batch_op.drop_constraint('fk_devoluciones_compra_tenant_id', type_='foreignkey')
        batch_op.drop_index('ix_devoluciones_compra_numero')
        batch_op.create_index('ix_devoluciones_compra_numero', ['numero'], unique=False)
        batch_op.create_index('uq_dev_compra_tenant_numero', ['tenant_id', 'numero'], unique=True)

    with op.batch_alter_table('cuentas_por_pagar', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cuentas_por_pagar_tenant_id', type_='foreignkey')
        batch_op.create_index('uq_cxp_tenant_documento', ['tenant_id', 'numero_documento'], unique=True)
        batch_op.create_index('ix_cuentas_por_pagar_numero_documento', ['numero_documento'], unique=False)

    with op.batch_alter_table('cuentas_por_cobrar', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cuentas_por_cobrar_tenant_id', type_='foreignkey')
        batch_op.create_index('uq_cxc_tenant_factura', ['tenant_id', 'numero_factura'], unique=True)
        batch_op.create_index('ix_cuentas_por_cobrar_numero_factura', ['numero_factura'], unique=False)

    with op.batch_alter_table('cotizaciones', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cotizaciones_tenant_id', type_='foreignkey')
        batch_op.drop_index('ix_cotizaciones_numero')
        batch_op.create_index('ix_cotizaciones_numero', ['numero'], unique=False)
        batch_op.create_index('uq_cotizaciones_tenant_numero', ['tenant_id', 'numero'], unique=True)

    with op.batch_alter_table('cotizaciones_detalles', schema=None) as batch_op:
        batch_op.drop_constraint('fk_cotizaciones_detalles_tenant_id', type_='foreignkey')

    with op.batch_alter_table('compras_documentos', schema=None) as batch_op:
        batch_op.drop_constraint('fk_compras_documentos_tenant_id', type_='foreignkey')
        batch_op.drop_index('ix_compras_documentos_numero')
        batch_op.create_index('ix_compras_documentos_numero', ['numero'], unique=False)
        batch_op.create_index('uq_compras_tenant_numero', ['tenant_id', 'numero'], unique=True)

    with op.batch_alter_table('compras_detalles', schema=None) as batch_op:
        batch_op.drop_constraint('fk_compras_detalles_tenant_id', type_='foreignkey')

    with op.batch_alter_table('clientes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_clientes_tenant_id', type_='foreignkey')
        batch_op.drop_constraint('uq_clientes_tenant_nit', type_='unique')
        batch_op.create_index('uq_clientes_tenant_nit', ['tenant_id', 'nit_cc'], unique=True)

    with op.batch_alter_table('centros_costo', schema=None) as batch_op:
        batch_op.drop_constraint('fk_centros_costo_tenant_id', type_='foreignkey')
        batch_op.drop_index('ix_centros_costo_codigo')
        batch_op.create_index('ix_centros_costo_codigo', ['codigo'], unique=False)
        batch_op.create_index('uq_cc_tenant_codigo', ['tenant_id', 'codigo'], unique=True)

    for table in reversed(_FK_ONLY_TABLES):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(f'fk_{table}_tenant_id', type_='foreignkey')
