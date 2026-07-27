"""Auditoria de aislamiento cross-tenant — modulo Auditoria (2026-07-24).

Encontrado en el barrido final: list_auditoria hacia un select(RegistroAuditoria)
sin ningun filtro de tenant, exponiendo el log completo de auditoria (quien
hizo que, cuando, sobre que entidad) de TODOS los tenants.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    apply_rls_tenant,
    reset_tenant_id,
    set_tenant_id,
)
from app.modules.auditoria.models import RegistroAuditoria


@pytest.mark.asyncio
async def test_list_auditoria_no_ve_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="aud-test", razon_social="Aud Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    db_session.add(RegistroAuditoria(
        usuario_email="secreto@t2.com", accion="Crear", entidad="Producto",
        descripcion="Evento secreto T2", tenant_id=2,
    ))
    await db_session.commit()
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)

    r = await client.get("/api/v1/auditoria", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(a["descripcion"] != "Evento secreto T2" for a in r.json())
