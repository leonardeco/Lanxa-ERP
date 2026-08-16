"""Run 2 — foundation multi-tenant: Tenant + tenant_id + JWT claim."""

from __future__ import annotations

import jwt
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.numbering import DocumentSequence, next_sequential_numero
from app.core.security import create_access_token
from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    get_tenant_id,
    set_tenant_id,
    reset_tenant_id,
)
@pytest.mark.asyncio
async def test_tenant_default_existe(db_session):
    t = await db_session.scalar(select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID))
    assert t is not None
    assert t.codigo == "superozono"


@pytest.mark.asyncio
async def test_usuario_admin_tiene_tenant(db_session):
    from app.modules.usuarios.models import Usuario

    u = await db_session.scalar(
        select(Usuario).where(Usuario.email == "admin@test.com")
    )
    assert u is not None
    assert u.tenant_id == DEFAULT_TENANT_ID


def test_jwt_incluye_tenant_id():
    token = create_access_token("42", tenant_id=7)
    payload = jwt.decode(
        token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM]
    )
    assert payload["sub"] == "42"
    assert payload["tenant_id"] == 7


def test_contextvar_tenant():
    reset_tenant_id()
    assert get_tenant_id() == DEFAULT_TENANT_ID
    set_tenant_id(9)
    assert get_tenant_id() == 9
    reset_tenant_id()
    assert get_tenant_id() == DEFAULT_TENANT_ID


@pytest.mark.asyncio
async def test_numbering_scoped_by_tenant(db_session):
    """Dos tenants no comparten el contador de prefijos."""
    from app.modules.ventas.models import VentaDocumento
    from app.core.tenancy import apply_rls_tenant

    set_tenant_id(1)
    await apply_rls_tenant(db_session, 1)
    n1 = await next_sequential_numero(db_session, VentaDocumento.numero, "LNX-V")
    assert n1 == "LNX-V-0001"

    # segundo tenant (tenants no tiene RLS)
    db_session.add(Tenant(
        id=2, codigo="otra", razon_social="Otra SAS", activo=True,
    ))
    await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    n2 = await next_sequential_numero(db_session, VentaDocumento.numero, "LNX-V")
    assert n2 == "LNX-V-0001"  # reinicia por tenant

    set_tenant_id(1)
    await apply_rls_tenant(db_session, 1)
    n3 = await next_sequential_numero(db_session, VentaDocumento.numero, "LNX-V")
    assert n3 == "LNX-V-0002"

    rows = (await db_session.execute(select(DocumentSequence))).scalars().all()
    by_t = {(r.tenant_id, r.prefix): r.last_value for r in rows}
    assert by_t[(1, "LNX-V")] == 2
    # con RLS activo en PG, desde tenant 1 no vemos filas de tenant 2
    if db_session.get_bind().dialect.name == "postgresql":
        assert (2, "LNX-V") not in by_t
    else:
        assert by_t.get((2, "LNX-V")) == 1
    reset_tenant_id()


@pytest.mark.asyncio
async def test_rls_oculta_productos_de_otro_tenant(db_session):
    """En Postgres, con GUC tenant=1 no se ven productos de tenant=2."""
    from decimal import Decimal
    from app.core.tenancy import apply_rls_tenant
    from app.modules.ventas.models import Producto

    if db_session.get_bind().dialect.name != "postgresql":
        pytest.skip("RLS solo en PostgreSQL")

    db_session.add(Tenant(id=2, codigo="otra", razon_social="Otra", activo=True))
    await db_session.flush()

    # stamp before_insert usa contextvar: hay que set_tenant_id además del GUC RLS
    set_tenant_id(1)
    await apply_rls_tenant(db_session, 1)
    db_session.add(Producto(
        sku="T1-A", nombre="Del tenant 1", marca="M",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=1,
    ))
    await db_session.flush()

    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    db_session.add(Producto(
        sku="T2-B", nombre="Del tenant 2", marca="M",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=2,
    ))
    await db_session.flush()

    set_tenant_id(1)
    await apply_rls_tenant(db_session, 1)
    visibles = (await db_session.execute(select(Producto))).scalars().all()
    skus = {p.sku for p in visibles}
    assert "T1-A" in skus
    assert "T2-B" not in skus
    reset_tenant_id()
