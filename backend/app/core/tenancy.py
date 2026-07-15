"""
Tenancy (Run 2 — multi-tenant foundation, ADR 0001).

- `Tenant`: empresa/suscriptor SaaS.
- `TenantScoped`: mixin ORM con `tenant_id` FK.
- Contexto por request (`contextvars`) fijado al autenticar; la numeración y
  futuros filtros leen `get_tenant_id()`.

RLS de Postgres (Run 3) se apoyará en la misma columna y en
`SET LOCAL app.tenant_id = ...` por conexión.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

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


class Tenant(Base):
    """Empresa / suscriptor (aislado por tenant_id en el resto de tablas)."""

    __tablename__ = "tenants"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str | None] = mapped_column(String(30))
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
