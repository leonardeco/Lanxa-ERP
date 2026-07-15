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

    class _Stub:
        # columna fake no usada para siembra (sin filas)
        pass

    # usar Producto.sku solo como columna "like" vacía — better use DocumentSequence path
    # with empty max from a real string column without matching rows
    from app.modules.ventas.models import VentaDocumento

    set_tenant_id(1)
    n1 = await next_sequential_numero(db_session, VentaDocumento.numero, "SOG-V")
    assert n1 == "SOG-V-0001"

    # segundo tenant
    db_session.add(Tenant(
        id=2, codigo="otra", razon_social="Otra SAS", activo=True,
    ))
    await db_session.flush()
    set_tenant_id(2)
    n2 = await next_sequential_numero(db_session, VentaDocumento.numero, "SOG-V")
    assert n2 == "SOG-V-0001"  # reinicia por tenant

    set_tenant_id(1)
    n3 = await next_sequential_numero(db_session, VentaDocumento.numero, "SOG-V")
    assert n3 == "SOG-V-0002"

    rows = (await db_session.execute(select(DocumentSequence))).scalars().all()
    by_t = {(r.tenant_id, r.prefix): r.last_value for r in rows}
    assert by_t[(1, "SOG-V")] == 2
    assert by_t[(2, "SOG-V")] == 1
    reset_tenant_id()
