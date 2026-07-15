"""RLS por tenant_id en PostgreSQL (Run 3, ADR 0001)

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-15

Solo PostgreSQL: ENABLE + FORCE ROW LEVEL SECURITY y política
`tenant_id = current_setting('app.tenant_id')`.

SQLite (LAN): no-op — RLS no existe; el aislamiento app-level sigue con
tenant_id + contextvar (Run 2).

La app debe ejecutar por transacción:
  SELECT set_config('app.tenant_id', '<id>', true);
(ver `app.core.tenancy.apply_rls_tenant`).
"""
from alembic import op

revision = "f7a8b9c0d1e2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None

# Mismas tablas tenant-scoped que e6f7a8b9c0d1 (+ document_sequences).
_TABLES = [
    "usuarios",
    "refresh_tokens",
    "productos",
    "clientes",
    "ventas_documentos",
    "ventas_detalles",
    "cotizaciones",
    "cotizaciones_detalles",
    "devoluciones_venta",
    "devoluciones_venta_detalles",
    "proveedores",
    "compras_documentos",
    "compras_detalles",
    "devoluciones_compra",
    "devoluciones_compra_detalles",
    "plan_cuentas",
    "centros_costo",
    "periodos_contables",
    "terceros",
    "asientos_contables",
    "movimientos_asiento",
    "saldos_iniciales",
    "cuentas_por_cobrar",
    "cuentas_por_pagar",
    "pagos",
    "parametros_tributarios",
    "parametros_nomina",
    "auditoria",
    "movimientos_inventario",
    "lotes",
    "document_sequences",
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in _TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        # missing_ok: true → NULL si no hay setting (ninguna fila visible hasta SET)
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON "{table}"
            FOR ALL
            USING (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::integer
            )
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::integer
            )
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    for table in reversed(_TABLES):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
