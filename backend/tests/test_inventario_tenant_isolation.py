"""Auditoria de aislamiento cross-tenant — modulo Inventario (2026-07-24).

inventario/router.py resulto ser 0% scoped: dashboard, lotes, movimientos
(kardex) y el ajuste manual no filtraban por tenant en absoluto.
"""
from __future__ import annotations

from datetime import date
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
from app.modules.inventario.models import (
    Lote,
    MovimientoInventario,
    OrigenMovimiento,
    TipoMovimientoInventario,
)
from app.modules.ventas.models import Producto


async def _en_tenant2(db_session):
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="inv-test", razon_social="Inv Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)


async def _al_tenant_default(db_session):
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)


@pytest.mark.asyncio
async def test_dashboard_inventario_no_cuenta_otro_tenant(
    client: AsyncClient, auth_headers: dict, db_session
):
    await _en_tenant2(db_session)
    producto = Producto(
        sku="T2-INV", nombre="Producto secreto T2", marca="X",
        precio_venta=Decimal("1"), precio_costo=Decimal("999999"),
        stock_actual=Decimal("500"), stock_minimo=Decimal("1"), tenant_id=2,
    )
    db_session.add(producto)
    await db_session.flush()
    db_session.add(Lote(
        producto_id=producto.id, codigo_lote="T2-LOTE",
        fecha_vencimiento=date(2026, 1, 1), cantidad_actual=Decimal("10"), tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/inventario/dashboard", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["valor_total_inventario"]) == 0.0
    assert body["lotes_vencidos"] == 0
    assert all(p["sku"] != "T2-INV" for p in body["top_productos_por_valor"])


@pytest.mark.asyncio
async def test_list_lotes_no_ve_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    producto = Producto(
        sku="T2-LOTE-P", nombre="Producto T2", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("10"), tenant_id=2,
    )
    db_session.add(producto)
    await db_session.flush()
    db_session.add(Lote(
        producto_id=producto.id, codigo_lote="T2-SECRETO",
        cantidad_actual=Decimal("5"), tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/inventario/lotes", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(l["codigo_lote"] != "T2-SECRETO" for l in r.json())


@pytest.mark.asyncio
async def test_list_movimientos_no_ve_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    producto = Producto(
        sku="T2-MOV-P", nombre="Producto T2", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("10"), tenant_id=2,
    )
    db_session.add(producto)
    await db_session.flush()
    db_session.add(MovimientoInventario(
        producto_id=producto.id, tipo=TipoMovimientoInventario.ENTRADA,
        origen=OrigenMovimiento.AJUSTE_MANUAL, cantidad=Decimal("5"),
        stock_antes=Decimal("0"), stock_despues=Decimal("5"),
        motivo="Movimiento secreto T2", tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/inventario/movimientos", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(m["motivo"] != "Movimiento secreto T2" for m in r.json())


@pytest.mark.asyncio
async def test_crear_ajuste_producto_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    producto = Producto(
        sku="T2-AJU-P", nombre="Producto T2", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("10"), tenant_id=2,
    )
    db_session.add(producto)
    await db_session.commit()
    await db_session.refresh(producto)
    producto_id = producto.id
    await _al_tenant_default(db_session)

    r = await client.post(
        "/api/v1/inventario/ajustes",
        json={"producto_id": producto_id, "tipo": "Entrada", "cantidad": 1, "motivo": "hackeado"},
        headers=auth_headers,
    )
    assert r.status_code == 404
