"""Auditoria de aislamiento cross-tenant — modulo Alegra (2026-07-24).

alegra/router.py resulto ser 0% scoped: ni una sola query filtraba por
tenant. Es el caso mas grave de la auditoria porque sync_cliente/
sync_producto empujan los datos leidos a un servicio EXTERNO (Alegra) —
un tenant podria terminar enviando el cliente/producto de OTRO tenant a
su propia cuenta de Alegra.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    apply_rls_tenant,
    reset_tenant_id,
    set_tenant_id,
)
from app.modules.alegra import router as alegra_router
from app.modules.ventas.models import Cliente, Producto, VentaDocumento


@pytest.fixture
def alegra_credenciales(monkeypatch):
    """Simula credenciales configuradas en .env (igual que test_alegra.py)."""
    monkeypatch.setattr(alegra_router.settings, "ALEGRA_EMAIL", "erp@superozono.test")
    monkeypatch.setattr(alegra_router.settings, "ALEGRA_TOKEN", "token-de-prueba")


async def _en_tenant2(db_session):
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="alegra-test", razon_social="Alegra Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)


async def _al_tenant_default(db_session):
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)


@pytest.mark.asyncio
async def test_sync_cliente_otro_tenant_404(
    client: AsyncClient, auth_headers: dict, db_session, alegra_credenciales, monkeypatch
):
    # Alegra "responde" ok — si esto se llega a invocar, el cliente de OTRO
    # tenant se habria empujado con exito a la cuenta de Alegra del caller.
    async def fake_post(path, payload):
        return {"id": 999, "name": payload.get("name")}
    monkeypatch.setattr(alegra_router, "alegra_post", fake_post)

    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-ALG", razon_social="Cliente secreto T2", tenant_id=2)
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    cliente_id = cliente.id
    await _al_tenant_default(db_session)

    r = await client.post(f"/api/v1/alegra/sync/cliente/{cliente_id}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_sync_producto_otro_tenant_404(
    client: AsyncClient, auth_headers: dict, db_session, alegra_credenciales, monkeypatch
):
    async def fake_post(path, payload):
        return {"id": 999, "name": payload.get("name")}
    monkeypatch.setattr(alegra_router, "alegra_post", fake_post)

    await _en_tenant2(db_session)
    producto = Producto(
        sku="T2-ALG", nombre="Producto secreto T2", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=2,
    )
    db_session.add(producto)
    await db_session.commit()
    await db_session.refresh(producto)
    producto_id = producto.id
    await _al_tenant_default(db_session)

    r = await client.post(f"/api/v1/alegra/sync/producto/{producto_id}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_enviar_factura_otro_tenant_404(
    client: AsyncClient, auth_headers: dict, db_session, alegra_credenciales, monkeypatch
):
    """Enviar a Alegra una venta que pertenece a OTRO tenant no debe ser
    posible ni siquiera para leerla — mucho menos facturarla."""
    async def fake_post(path, payload):
        return {"id": 999, "numberTemplate": {"fullNumber": "F-999"}, "stamp": {"cufe": "x"}}
    monkeypatch.setattr(alegra_router, "alegra_post", fake_post)

    await _en_tenant2(db_session)
    cliente = Cliente(
        nit_cc="T2-ALG-V", razon_social="Cliente venta T2", alegra_id=1, tenant_id=2,
    )
    db_session.add(cliente)
    await db_session.flush()
    venta = VentaDocumento(
        numero="T2-ALG-V-0001", cliente_id=cliente.id, total=Decimal("100"), tenant_id=2,
    )
    db_session.add(venta)
    await db_session.commit()
    await db_session.refresh(venta)
    venta_id = venta.id
    await _al_tenant_default(db_session)

    r = await client.post(f"/api/v1/alegra/facturas/{venta_id}", headers=auth_headers)
    assert r.status_code == 404
