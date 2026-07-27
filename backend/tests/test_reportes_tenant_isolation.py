"""Auditoria de aislamiento cross-tenant — modulo Reportes (2026-07-24).

reportes/router.py mezclaba datos de todos los tenants en compras-periodo,
ventas-periodo, retenciones-periodo, y — el mas grave — los estados
financieros (estado-resultados / balance-general), construidos sobre el
libro diario (asientos contables) sin filtrar por tenant.
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
from app.modules.compras.models import CompraDocumento, Proveedor
from app.modules.contabilidad.models import (
    AsientoContable,
    ClaseCuenta,
    MovimientoAsiento,
    NaturalezaCuenta,
    PlanCuentas,
)
from app.modules.ventas.models import Cliente, EstadoVenta, Producto, VentaDetalle, VentaDocumento


async def _en_tenant2(db_session):
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="rep-test", razon_social="Rep Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)


async def _al_tenant_default(db_session):
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)


@pytest.mark.asyncio
async def test_compras_periodo_no_cuenta_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    proveedor = Proveedor(nit_cc="T2-REP-PROV", razon_social="Proveedor Secreto T2", tenant_id=2)
    db_session.add(proveedor)
    await db_session.flush()
    hoy = date.today()
    db_session.add(CompraDocumento(
        numero="T2-REP-CP", fecha=hoy, proveedor_id=proveedor.id,
        proveedor_razon_social="Proveedor Secreto T2", total=Decimal("999999"),
        estado="Confirmada", tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/reportes/compras-periodo", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["total"]) == 0.0
    assert body["cantidad_documentos"] == 0
    assert all(p["nombre"] != "Proveedor Secreto T2" for p in body["por_proveedor"])


@pytest.mark.asyncio
async def test_ventas_periodo_no_cuenta_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cliente = Cliente(nit_cc="T2-REP-CLI", razon_social="Cliente Secreto T2", tenant_id=2)
    producto = Producto(
        sku="T2-REP-PROD", nombre="Producto T2", marca="MarcaSecretaRep",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=2,
    )
    db_session.add_all([cliente, producto])
    await db_session.flush()
    hoy = date.today()
    venta = VentaDocumento(
        numero="T2-REP-V", fecha=hoy, cliente_id=cliente.id, total=Decimal("999999"), tenant_id=2,
    )
    db_session.add(venta)
    await db_session.flush()
    db_session.add(VentaDetalle(
        venta_id=venta.id, producto_id=producto.id, precio_unitario=Decimal("999999"),
        total_linea=Decimal("999999"), tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/reportes/ventas-periodo", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["total"]) == 0.0
    assert body["cantidad_documentos"] == 0
    assert all(c["nombre"] != "Cliente Secreto T2" for c in body["por_cliente"])
    assert all(m["nombre"] != "MarcaSecretaRep" for m in body["por_marca"])


@pytest.mark.asyncio
async def test_retenciones_periodo_no_cuenta_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    proveedor = Proveedor(nit_cc="T2-REP-PROV2", razon_social="Proveedor T2", tenant_id=2)
    cliente = Cliente(nit_cc="T2-REP-CLI2", razon_social="Cliente T2", tenant_id=2)
    db_session.add_all([proveedor, cliente])
    await db_session.flush()
    hoy = date.today()
    db_session.add(CompraDocumento(
        numero="T2-REP-CP2", fecha=hoy, proveedor_id=proveedor.id, total=Decimal("100"),
        retefuente=Decimal("5000"), reteiva=Decimal("3000"), reteica=Decimal("1000"),
        estado="Confirmada", tenant_id=2,
    ))
    db_session.add(VentaDocumento(
        numero="T2-REP-V2", fecha=hoy, cliente_id=cliente.id, total=Decimal("100"),
        retefuente=Decimal("5000"), reteiva=Decimal("3000"), reteica=Decimal("1000"),
        tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/reportes/retenciones-periodo", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["compras_retefuente"]) == 0.0
    assert float(body["ventas_retefuente"]) == 0.0
    assert float(body["total_retefuente"]) == 0.0


async def _crear_asiento_otro_tenant(db_session, *, clase: ClaseCuenta, codigo_puc: str) -> None:
    await _en_tenant2(db_session)
    cuenta = PlanCuentas(
        codigo_puc=codigo_puc, nombre=f"Cuenta secreta T2 {codigo_puc}",
        clase=clase, naturaleza=NaturalezaCuenta.DEBITO, tenant_id=2,
    )
    db_session.add(cuenta)
    await db_session.flush()
    asiento = AsientoContable(
        fecha=date.today(), descripcion="Asiento secreto T2", tenant_id=2,
    )
    db_session.add(asiento)
    await db_session.flush()
    db_session.add(MovimientoAsiento(
        asiento_id=asiento.id, cuenta_id=cuenta.id,
        debito=Decimal("999999"), credito=Decimal("0"), tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)


@pytest.mark.asyncio
async def test_estado_resultados_no_cuenta_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _crear_asiento_otro_tenant(db_session, clase=ClaseCuenta.GASTO, codigo_puc="T2-5199")

    hoy = date.today()
    r = await client.get(
        "/api/v1/reportes/estado-resultados",
        params={"fecha_desde": hoy.replace(day=1).isoformat(), "fecha_hasta": hoy.isoformat()},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(c["codigo_puc"] != "T2-5199" for c in body["gastos"]["cuentas"])
    assert float(body["gastos"]["total"]) == 0.0


@pytest.mark.asyncio
async def test_balance_general_no_cuenta_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _crear_asiento_otro_tenant(db_session, clase=ClaseCuenta.ACTIVO, codigo_puc="T2-1105")

    r = await client.get("/api/v1/reportes/balance-general", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(c["codigo_puc"] != "T2-1105" for c in body["activo"]["cuentas"])
    assert float(body["total_activo"]) == 0.0
