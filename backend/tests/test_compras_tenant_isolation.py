"""Auditoria de aislamiento cross-tenant — modulo Compras (2026-07-24)."""
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
from app.modules.compras.models import CompraDetalle, CompraDocumento, DevolucionCompra, Proveedor
from app.modules.ventas.models import Producto


async def _en_tenant2(db_session):
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="compras-test", razon_social="Compras Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)


async def _al_tenant_default(db_session):
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)


@pytest.mark.asyncio
async def test_dashboard_compras_no_cuenta_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    proveedor = Proveedor(nit_cc="T2-PROV", razon_social="Proveedor secreto T2", tenant_id=2)
    db_session.add(proveedor)
    await db_session.flush()
    hoy = date.today()
    db_session.add(CompraDocumento(
        numero="T2-CP-0001", fecha=hoy, proveedor_id=proveedor.id,
        proveedor_razon_social="Proveedor secreto T2", total=Decimal("999999"),
        estado="Confirmada", estado_pago="Pendiente", tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/compras/dashboard", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["total_compras_mes"]) == 0.0
    assert body["cantidad_compras_mes"] == 0
    assert body["total_proveedores_activos"] == 0
    assert float(body["cxp_pendiente"]) == 0.0
    assert all(p["proveedor"] != "Proveedor secreto T2" for p in body["top_proveedores"])


@pytest.mark.asyncio
async def test_crear_compra_proveedor_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    proveedor = Proveedor(nit_cc="T2-PROV-2", razon_social="Proveedor T2", tenant_id=2)
    db_session.add(proveedor)
    await db_session.commit()
    await db_session.refresh(proveedor)
    proveedor_id = proveedor.id
    await _al_tenant_default(db_session)

    r = await client.post(
        "/api/v1/compras/",
        json={
            "proveedor_id": proveedor_id,
            "fecha": "2026-01-01",
            "detalles": [{
                "descripcion": "Item", "cantidad": 1, "precio_unitario": 100,
                "descuento_porcentaje": 0, "iva_porcentaje": 19,
            }],
        },
        headers=auth_headers,
    )
    assert r.status_code == 404


async def _crear_compra_otro_tenant(db_session, *, estado="Borrador") -> int:
    await _en_tenant2(db_session)
    proveedor = Proveedor(nit_cc="T2-PROV-3", razon_social="Proveedor T2", tenant_id=2)
    db_session.add(proveedor)
    await db_session.flush()
    compra = CompraDocumento(
        numero="T2-CP-0002", fecha=date(2026, 1, 1), proveedor_id=proveedor.id,
        proveedor_razon_social=proveedor.razon_social, total=Decimal("100"),
        estado=estado, tenant_id=2,
    )
    db_session.add(compra)
    await db_session.commit()
    await db_session.refresh(compra)
    compra_id = compra.id
    await _al_tenant_default(db_session)
    return compra_id


@pytest.mark.asyncio
async def test_confirmar_compra_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    compra_id = await _crear_compra_otro_tenant(db_session, estado="Borrador")
    r = await client.post(f"/api/v1/compras/{compra_id}/confirmar", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_anular_compra_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    compra_id = await _crear_compra_otro_tenant(db_session, estado="Confirmada")
    r = await client.post(f"/api/v1/compras/{compra_id}/anular", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_devoluciones_compra_otro_tenant_vacio(client: AsyncClient, auth_headers: dict, db_session):
    """El listado de devoluciones de una compra de OTRO tenant no debe
    devolver sus notas debito (usando el id de la compra de otro tenant)."""
    await _en_tenant2(db_session)
    proveedor = Proveedor(nit_cc="T2-PROV-4", razon_social="Proveedor T2", tenant_id=2)
    db_session.add(proveedor)
    await db_session.flush()
    compra = CompraDocumento(
        numero="T2-CP-0003", fecha=date(2026, 1, 1), proveedor_id=proveedor.id,
        proveedor_razon_social=proveedor.razon_social, total=Decimal("100"),
        estado="Confirmada", tenant_id=2,
    )
    db_session.add(compra)
    await db_session.flush()
    db_session.add(DevolucionCompra(
        numero="T2-ND-0001", compra_id=compra.id, fecha=date(2026, 1, 2),
        motivo="Devolucion secreta T2", tenant_id=2,
    ))
    await db_session.commit()
    await db_session.refresh(compra)
    compra_id = compra.id
    await _al_tenant_default(db_session)

    r = await client.get(f"/api/v1/compras/{compra_id}/devoluciones", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json() == []


@pytest.mark.asyncio
async def test_crear_devolucion_compra_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    """Con una linea de detalle real (compra_detalle_id valido) para que el
    404 solo pueda venir del chequeo de tenant, no de 'linea no pertenece'."""
    await _en_tenant2(db_session)
    proveedor = Proveedor(nit_cc="T2-PROV-5", razon_social="Proveedor T2", tenant_id=2)
    db_session.add(proveedor)
    await db_session.flush()
    compra = CompraDocumento(
        numero="T2-CP-0004", fecha=date(2026, 1, 1), proveedor_id=proveedor.id,
        proveedor_razon_social=proveedor.razon_social, total=Decimal("100"),
        estado="Confirmada", tenant_id=2,
    )
    db_session.add(compra)
    await db_session.flush()
    detalle = CompraDetalle(
        compra_id=compra.id, descripcion="Item T2", cantidad=Decimal("1"),
        precio_unitario=Decimal("100"), tenant_id=2,
    )
    db_session.add(detalle)
    await db_session.commit()
    await db_session.refresh(compra)
    await db_session.refresh(detalle)
    compra_id, detalle_id = compra.id, detalle.id
    await _al_tenant_default(db_session)

    r = await client.post(
        f"/api/v1/compras/{compra_id}/devoluciones",
        json={"motivo": "hackeado", "detalles": [{"compra_detalle_id": detalle_id, "cantidad": 1}]},
        headers=auth_headers,
    )
    assert r.status_code == 404
