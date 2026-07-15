"""Run 5: uniques compuestos (tenant_id, clave de negocio)

Revision ID: a0b1c2d3e4f5
Revises: f7a8b9c0d1e2
Create Date: 2026-07-15

Permite el mismo SKU/email/NIT/numero en tenants distintos.
Sustituye índices UNIQUE globales por UNIQUE(tenant_id, col).
"""
from alembic import op

revision = "a0b1c2d3e4f5"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None

# (table, old_unique_index_name, column, new_unique_index_name)
_INDEXES = [
    ("productos", "ix_productos_sku", "sku", "uq_productos_tenant_sku"),
    ("usuarios", "ix_usuarios_email", "email", "uq_usuarios_tenant_email"),
    ("clientes", "ix_clientes_nit_cc", "nit_cc", "uq_clientes_tenant_nit"),
    ("proveedores", "ix_proveedores_nit_cc", "nit_cc", "uq_proveedores_tenant_nit"),
    ("ventas_documentos", "ix_ventas_documentos_numero", "numero", "uq_ventas_tenant_numero"),
    ("cotizaciones", "ix_cotizaciones_numero", "numero", "uq_cotizaciones_tenant_numero"),
    ("devoluciones_venta", "ix_devoluciones_venta_numero", "numero", "uq_dev_venta_tenant_numero"),
    ("compras_documentos", "ix_compras_documentos_numero", "numero", "uq_compras_tenant_numero"),
    ("devoluciones_compra", "ix_devoluciones_compra_numero", "numero", "uq_dev_compra_tenant_numero"),
    ("plan_cuentas", "ix_plan_cuentas_codigo_puc", "codigo_puc", "uq_puc_tenant_codigo"),
    ("centros_costo", "ix_centros_costo_codigo", "codigo", "uq_cc_tenant_codigo"),
    ("pagos", "ix_pagos_numero_comprobante", "numero_comprobante", "uq_pagos_tenant_numero"),
    ("terceros", "ix_terceros_nit_cc", "nit_cc", "uq_terceros_tenant_nit"),
    ("cuentas_por_cobrar", "ix_cuentas_por_cobrar_numero_factura", "numero_factura", "uq_cxc_tenant_factura"),
    ("cuentas_por_pagar", "ix_cuentas_por_pagar_numero_documento", "numero_documento", "uq_cxp_tenant_documento"),
    ("parametros_tributarios", "ix_parametros_tributarios_concepto", "concepto", "uq_param_trib_tenant_concepto"),
    ("parametros_nomina", "ix_parametros_nomina_concepto", "concepto", "uq_param_nom_tenant_concepto"),
]


def _drop_index_if_exists(table: str, name: str) -> None:
    bind = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(bind)
    existing = {ix["name"] for ix in inspector.get_indexes(table)}
    # unique constraints may appear as indexes
    if name in existing:
        op.drop_index(name, table_name=table)
        return
    # SQLite autoindex names for UNIQUE columns
    for ix in inspector.get_indexes(table):
        if ix.get("unique") and ix["column_names"] == [name.split("_")[-1] if False else None]:
            pass
    # try common autoindex patterns by column
    for ix in inspector.get_indexes(table):
        cols = ix.get("column_names") or []
        if ix.get("unique") and len(cols) == 1:
            # match by unique single-column index if name mismatch
            if name.endswith(cols[0]) or cols[0] in name:
                try:
                    op.drop_index(ix["name"], table_name=table)
                    return
                except Exception:
                    continue
    # last resort: drop by provided name ignoring errors
    try:
        op.drop_index(name, table_name=table)
    except Exception:
        pass


def upgrade() -> None:
    bind = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(bind)
    tables = set(inspector.get_table_names())

    for table, old_ix, col, new_ix in _INDEXES:
        if table not in tables:
            continue
        # Drop old unique single-column index if present
        idxs = {ix["name"]: ix for ix in inspector.get_indexes(table)}
        if old_ix in idxs:
            op.drop_index(old_ix, table_name=table)
        else:
            for ix in inspector.get_indexes(table):
                cols = ix.get("column_names") or []
                if ix.get("unique") and cols == [col]:
                    op.drop_index(ix["name"], table_name=table)
                    break
        # Non-unique helper index on the business column (optional, useful for search)
        try:
            op.create_index(f"ix_{table}_{col}", table, [col], unique=False)
        except Exception:
            pass
        op.create_index(new_ix, table, ["tenant_id", col], unique=True)
        # refresh inspector for next table
        inspector = __import__("sqlalchemy").inspect(bind)

def downgrade() -> None:
    bind = op.get_bind()
    inspector = __import__("sqlalchemy").inspect(bind)
    tables = set(inspector.get_table_names())

    for table, old_ix, col, new_ix in reversed(_INDEXES):
        if table not in tables:
            continue
        try:
            op.drop_index(new_ix, table_name=table)
        except Exception:
            pass
        try:
            op.create_index(old_ix, table, [col], unique=True)
        except Exception:
            pass
