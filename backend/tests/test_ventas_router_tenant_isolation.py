"""Auditoria de aislamiento cross-tenant — modulo Ventas, ventas/router.py
(2026-07-24).

Encontrado al terminar la auditoria de los demas modulos: ventas/router.py
tenia 11 puntos con el mismo patron (session.get/db.get sin scope, o bare
select sin for_tenant/tenant_clause) que se habian quedado sin corregir
pese a estar en la lista original de la revision de Run 6 — incluye el
bug de list_cotizaciones/get_cotizacion ya documentado (sin corregir)
desde 2026-07-23 en la memoria de infraestructura del proyecto.
"""
from __future__ import annotations

from datetime import date, timedelta
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
from app.modules.ventas.models import (
    Cliente,
    Cotizacion,
    DevolucionVenta,
    EstadoCotizacion,
    EstadoVenta,
    Producto,
    VentaDetalle,
    VentaDocumento,
)


async def _en_tenant2(db_session):
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="ventas-rtr-test", razon_social="Ventas RTR Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)


async def _al_tenant_default(db_session):
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)


@pytest.mark.asyncio
async def test_update_delete_cliente_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-VR-CLI", razon_social="Cliente secreto T2", tenant_id=2)
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    cliente_id = cliente.id
    await _al_tenant_default(db_session)

    r = await client.put(
        f"/api/v1/ventas/clientes/{cliente_id}", json={"razon_social": "hackeado"}, headers=auth_headers
    )
    assert r.status_code == 404
    r = await client.delete(f"/api/v1/ventas/clientes/{cliente_id}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_producto_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    producto = Producto(
        sku="T2-VR-DELP", nombre="Producto secreto T2", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=2,
    )
    db_session.add(producto)
    await db_session.commit()
    await db_session.refresh(producto)
    producto_id = producto.id
    await _al_tenant_default(db_session)

    r = await client.delete(f"/api/v1/ventas/productos/{producto_id}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_venta_cliente_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-VR-CLI2", razon_social="Cliente T2", tenant_id=2)
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    cliente_id = cliente.id
    await _al_tenant_default(db_session)

    producto_r = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "T1-VR-CV-P", "nombre": "Propio", "marca": "X", "precio_venta": "100", "stock_actual": 1},
        headers=auth_headers,
    )
    assert producto_r.status_code == 201, producto_r.text

    r = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": "2026-01-01",
            "cliente_id": cliente_id,
            "detalles": [{"producto_id": producto_r.json()["id"], "cantidad": 1, "precio_unitario": 100}],
        },
        headers=auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_venta_producto_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    """El producto de la linea de detalle pertenece a otro tenant."""
    await _en_tenant2(db_session)
    producto = Producto(
        sku="T2-VR-PROD", nombre="Producto T2", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=2,
    )
    db_session.add(producto)
    await db_session.commit()
    await db_session.refresh(producto)
    producto_id = producto.id
    await _al_tenant_default(db_session)

    cliente_r = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "T1-VR-OWN", "razon_social": "Propio"},
        headers=auth_headers,
    )
    assert cliente_r.status_code == 201, cliente_r.text

    r = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": "2026-01-01",
            "cliente_id": cliente_r.json()["id"],
            "detalles": [{"producto_id": producto_id, "cantidad": 1, "precio_unitario": 100}],
        },
        headers=auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_cotizacion_cliente_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-VR-CLI3", razon_social="Cliente T2", tenant_id=2)
    db_session.add(cliente)
    await db_session.commit()
    await db_session.refresh(cliente)
    cliente_id = cliente.id
    await _al_tenant_default(db_session)

    producto_r = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "T1-VR-COT-P", "nombre": "Propio", "marca": "X", "precio_venta": "100", "stock_actual": 1},
        headers=auth_headers,
    )
    assert producto_r.status_code == 201, producto_r.text

    r = await client.post(
        "/api/v1/ventas/cotizaciones",
        json={
            "fecha": "2026-01-01",
            "cliente_id": cliente_id,
            "detalles": [{"producto_id": producto_r.json()["id"], "cantidad": 1, "precio_unitario": 100}],
        },
        headers=auth_headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_y_get_cotizacion_no_ve_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    """Bug pre-existente documentado desde 2026-07-23 (memoria de infra):
    list_cotizaciones/get_cotizacion hacian un select(Cotizacion) sin ningun
    filtro de tenant."""
    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-VR-CLI4", razon_social="Cliente T2", tenant_id=2)
    db_session.add(cliente)
    await db_session.flush()
    hoy = date.today()
    cot = Cotizacion(
        numero="T2-COT-0001", fecha=hoy, vigencia_dias=15,
        fecha_vencimiento=hoy + timedelta(days=15), cliente_id=cliente.id,
        estado=EstadoCotizacion.BORRADOR, tenant_id=2,
    )
    db_session.add(cot)
    await db_session.commit()
    await db_session.refresh(cot)
    cot_id = cot.id
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/ventas/cotizaciones", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(c["numero"] != "T2-COT-0001" for c in r.json())

    r = await client.get(f"/api/v1/ventas/cotizaciones/{cot_id}", headers=auth_headers)
    assert r.status_code == 404


async def _crear_venta_otro_tenant(db_session, *, estado: EstadoVenta) -> int:
    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-VR-CLI5", razon_social="Cliente T2", tenant_id=2)
    db_session.add(cliente)
    await db_session.flush()
    venta = VentaDocumento(
        numero="T2-VR-V0001", fecha=date(2026, 1, 1), cliente_id=cliente.id,
        total=Decimal("100"), estado=estado, tenant_id=2,
    )
    db_session.add(venta)
    await db_session.commit()
    await db_session.refresh(venta)
    venta_id = venta.id
    await _al_tenant_default(db_session)
    return venta_id


@pytest.mark.asyncio
async def test_confirmar_venta_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    venta_id = await _crear_venta_otro_tenant(db_session, estado=EstadoVenta.BORRADOR)
    r = await client.post(f"/api/v1/ventas/{venta_id}/confirmar", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_anular_venta_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    venta_id = await _crear_venta_otro_tenant(db_session, estado=EstadoVenta.CONFIRMADA)
    r = await client.post(f"/api/v1/ventas/{venta_id}/anular", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_devoluciones_venta_otro_tenant_vacio(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-VR-CLI6", razon_social="Cliente T2", tenant_id=2)
    db_session.add(cliente)
    await db_session.flush()
    venta = VentaDocumento(
        numero="T2-VR-V0002", fecha=date(2026, 1, 1), cliente_id=cliente.id,
        total=Decimal("100"), estado=EstadoVenta.CONFIRMADA, tenant_id=2,
    )
    db_session.add(venta)
    await db_session.flush()
    db_session.add(DevolucionVenta(
        numero="T2-VR-NC0001", venta_id=venta.id, fecha=date(2026, 1, 2),
        motivo="Devolucion secreta T2", tenant_id=2,
    ))
    await db_session.commit()
    await db_session.refresh(venta)
    venta_id = venta.id
    await _al_tenant_default(db_session)

    r = await client.get(f"/api/v1/ventas/{venta_id}/devoluciones", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json() == []


@pytest.mark.asyncio
async def test_crear_devolucion_venta_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-VR-CLI7", razon_social="Cliente T2", tenant_id=2)
    producto = Producto(
        sku="T2-VR-DEV-P", nombre="Producto T2", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("10"), tenant_id=2,
    )
    db_session.add_all([cliente, producto])
    await db_session.flush()
    venta = VentaDocumento(
        numero="T2-VR-V0003", fecha=date(2026, 1, 1), cliente_id=cliente.id,
        total=Decimal("100"), estado=EstadoVenta.CONFIRMADA, tenant_id=2,
    )
    db_session.add(venta)
    await db_session.flush()
    detalle = VentaDetalle(
        venta_id=venta.id, producto_id=producto.id, cantidad=Decimal("1"),
        precio_unitario=Decimal("100"), total_linea=Decimal("100"), tenant_id=2,
    )
    db_session.add(detalle)
    await db_session.commit()
    await db_session.refresh(venta)
    await db_session.refresh(detalle)
    venta_id, detalle_id = venta.id, detalle.id
    await _al_tenant_default(db_session)

    r = await client.post(
        f"/api/v1/ventas/{venta_id}/devoluciones",
        json={"motivo": "hackeado", "detalles": [{"venta_detalle_id": detalle_id, "cantidad": 1}]},
        headers=auth_headers,
    )
    assert r.status_code == 404
