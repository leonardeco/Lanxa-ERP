"""tenants + tenant_id en tablas de negocio (Run 2 foundation, ADR 0001)

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-15

1. Crea `tenants` y siembra la empresa #1 (Super Ozono / LAN).
2. Agrega `tenant_id` NOT NULL DEFAULT 1 a tablas de datos.
3. Rehace `document_sequences` con PK compuesta (tenant_id, prefix).

RLS (Run 3) y filtros automáticos en todos los queries vendrán después.
"""
from alembic import op
import sqlalchemy as sa

revision = "e6f7a8b9c0d1"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None

# Tablas de negocio que reciben tenant_id (no incluye alembic_version ni tenants).
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
]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("razon_social", sa.String(length=200), nullable=False),
        sa.Column("nit", sa.String(length=30), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )
    op.create_index("ix_tenants_codigo", "tenants", ["codigo"])

    # Empresa #1 — datos del despliegue LAN actual
    op.execute(
        sa.text(
            "INSERT INTO tenants (id, codigo, razon_social, nit, activo, notas) "
            "VALUES (1, 'superozono', "
            "'TECNOLOGIA E INNOVACION SUPER OZONO S.A.S.', "
            "'901841798-5', 1, "
            "'Tenant por defecto — despliegue LAN v0.3.x / Run 2 foundation')"
        )
    )

    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    for table in _TABLES:
        if table not in existing:
            continue
        cols = {c["name"] for c in inspector.get_columns(table)}
        if "tenant_id" in cols:
            continue
        # SQLite no soporta ADD COLUMN con FK inline; la FK se declara en el ORM
        # y en Postgres se crea con create_foreign_key.
        op.add_column(
            table,
            sa.Column(
                "tenant_id",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        if not is_sqlite:
            op.create_foreign_key(
                f"fk_{table}_tenant_id",
                table,
                "tenants",
                ["tenant_id"],
                ["id"],
                ondelete="RESTRICT",
            )

    # document_sequences: PK compuesta (tenant_id, prefix)
    if "document_sequences" in existing:
        op.rename_table("document_sequences", "document_sequences_old")
        op.create_table(
            "document_sequences",
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("prefix", sa.String(length=32), nullable=False),
            sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("tenant_id", "prefix"),
        )
        if not is_sqlite:
            op.create_foreign_key(
                "fk_document_sequences_tenant_id",
                "document_sequences",
                "tenants",
                ["tenant_id"],
                ["id"],
                ondelete="RESTRICT",
            )
        op.execute(
            sa.text(
                "INSERT INTO document_sequences (tenant_id, prefix, last_value) "
                "SELECT 1, prefix, last_value FROM document_sequences_old"
            )
        )
        op.drop_table("document_sequences_old")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "document_sequences" in existing:
        op.rename_table("document_sequences", "document_sequences_new")
        op.create_table(
            "document_sequences",
            sa.Column("prefix", sa.String(length=32), nullable=False),
            sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("prefix"),
        )
        op.execute(
            sa.text(
                "INSERT INTO document_sequences (prefix, last_value) "
                "SELECT prefix, last_value FROM document_sequences_new WHERE tenant_id = 1"
            )
        )
        op.drop_table("document_sequences_new")

    for table in reversed(_TABLES):
        if table not in existing:
            continue
        cols = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        if "tenant_id" not in cols:
            continue
        try:
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        except Exception:
            pass
        op.drop_column(table, "tenant_id")

    op.drop_index("ix_tenants_codigo", table_name="tenants")
    op.drop_table("tenants")
