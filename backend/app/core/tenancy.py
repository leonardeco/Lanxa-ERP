"""
Tenancy (Run 2 foundation + Run 3 RLS, ADR 0001).

- `Tenant`: empresa/suscriptor SaaS.
- `TenantScoped`: mixin ORM con `tenant_id` FK.
- Contexto por request (`contextvars`) fijado al autenticar.
- Postgres RLS: `apply_rls_tenant` ejecuta
  `set_config('app.tenant_id', …, true)` (LOCAL a la transacción).
  SQLite: no-op (LAN).
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, event, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, Mapper, mapped_column
from sqlalchemy.sql import Select

from app.core.database import Base
from app.core.time import utcnow

# 1 = Super Ozono (tenant LAN / empresa #1). Constante de seed y fallback.
DEFAULT_TENANT_ID = 1

_tenant_ctx: ContextVar[int | None] = ContextVar("tenant_id", default=None)


def get_tenant_id() -> int:
    """Tenant del request actual. Fallback al default LAN si aún no hay auth."""
    tid = _tenant_ctx.get()
    return DEFAULT_TENANT_ID if tid is None else tid


def set_tenant_id(tenant_id: int | None) -> None:
    _tenant_ctx.set(tenant_id)


def reset_tenant_id() -> None:
    _tenant_ctx.set(None)


async def apply_rls_tenant(
    session: AsyncSession, tenant_id: int | None = None
) -> None:
    """Fija `app.tenant_id` en la transacción actual (solo PostgreSQL).

    Debe llamarse al abrir la sesión de request y de nuevo tras autenticar si
    el tenant del JWT difiere del default.
    """
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    tid = DEFAULT_TENANT_ID if tenant_id is None else int(tenant_id)
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tid)},
    )


# Tablas con política tenant_isolation (Run 3). Mantener alineado con
# alembic/versions/f7a8b9c0d1e2_rls_postgres.py
RLS_TABLES: tuple[str, ...] = (
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
    "ventas_diarias",
    "ventas_diarias_detalles",
    "pagos_sueltos_diarios",
)


def enable_postgres_rls_on_connection(sync_conn) -> None:
    """Activa RLS+FORCE+política en una conexión sync (tests / utilidades).

    No-op si el dialecto no es PostgreSQL. Idempotente (DROP POLICY IF EXISTS).
    """
    if sync_conn.dialect.name != "postgresql":
        return
    for table in RLS_TABLES:
        sync_conn.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
        sync_conn.execute(text(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY'))
        sync_conn.execute(text(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}"'))
        sync_conn.execute(
            text(
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
        )


class Tenant(Base):
    """Empresa / suscriptor (aislado por tenant_id en el resto de tablas)."""

    __tablename__ = "tenants"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str | None] = mapped_column(String(30))
    # dominio: parte después del @ en los emails de este tenant (minúsculas, sin @).
    # Ej: "superozonoglobal.com". Se usa para resolver tenant en el login antes
    # de buscar al usuario — evita la colisión de emails iguales entre tenants.
    # Debe almacenarse ya normalizado (minúsculas). Null solo si el tenant aún
    # no fue configurado; en ese caso el login falla con error claro.
    dominio: Mapped[str | None] = mapped_column(String(200), unique=True, index=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )


class TenantScoped:
    """Mixin: toda fila de negocio pertenece a un tenant."""

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        server_default=str(DEFAULT_TENANT_ID),
        default=DEFAULT_TENANT_ID,
    )


# ── Run 4: filtros y stamp explícitos (defensa además de RLS) ─────────


def tenant_clause(model):
    """Expresión SQLAlchemy: `model.tenant_id == get_tenant_id()`."""
    return model.tenant_id == get_tenant_id()


def for_tenant(stmt: Select, model) -> Select:
    """Añade el filtro de tenant a un `select(Model)` (o join cuya entidad sea model)."""
    return stmt.where(tenant_clause(model))


async def get_for_tenant(session: AsyncSession, model, entity_id: int):
    """Carga por id solo si pertenece al tenant actual (None si no existe / otro tenant)."""
    return await session.scalar(
        select(model).where(model.id == entity_id, tenant_clause(model))
    )


def stamp_tenant(obj):
    """Asigna `tenant_id` del request al objeto ORM (altas)."""
    if hasattr(obj, "tenant_id"):
        obj.tenant_id = get_tenant_id()
    return obj


@event.listens_for(Mapper, "before_insert")
def _auto_stamp_tenant(mapper: Mapper, connection, target) -> None:  # noqa: ARG001
    """Al insertar filas tenant-scoped, fuerza el tenant del contextvar.

    `Tenant` (catálogo de empresas) no se toca. Si el contextvar no está fijado,
    se usa DEFAULT_TENANT_ID (LAN).
    """
    if target.__class__.__name__ == "Tenant":
        return
    if "tenant_id" not in mapper.columns:
        return
    target.tenant_id = get_tenant_id()
