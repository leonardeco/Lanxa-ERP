"""Auditoria de aislamiento cross-tenant — modulo Contabilidad (2026-07-24).

Encontrado en la revision final de Run 6: la gran mayoria de endpoints de
`contabilidad/router.py` no filtraban por tenant (bare `select()`/`db.get()`),
a diferencia de usuarios/router.py y ventas/router.py que ya se habian
corregido. Cada test aqui confirma (RED) el hueco contra el codigo sin
corregir antes del fix correspondiente en router.py.
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
from app.modules.contabilidad.models import (
    AsientoContable,
    CentroCosto,
    ClaseCuenta,
    CuentaPorCobrar,
    CuentaPorPagar,
    NaturalezaCuenta,
    Pago,
    ParametroNomina,
    ParametroTributario,
    PeriodoContable,
    PlanCuentas,
    Tercero,
    TipoPago,
    TipoTercero,
)


async def _en_tenant2(db_session):
    """Context manager-ish helper: crea el Tenant 2 si no existe y cambia el
    contexto activo a el. El caller debe restaurar con `_al_tenant_default`."""
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="cont-test", razon_social="Cont Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)


async def _al_tenant_default(db_session):
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)


@pytest.mark.asyncio
async def test_dashboard_contable_no_cuenta_otro_tenant(
    client: AsyncClient, auth_headers: dict, db_session
):
    """El dashboard cuenta PUC/centros/periodos/terceros/parametros de TODOS
    los tenants en vez de solo el propio."""
    await _en_tenant2(db_session)
    db_session.add(Tercero(
        nit_cc="T2-999", razon_social="Tercero secreto", tipo=TipoTercero.CLIENTE, tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/contabilidad/dashboard", headers=auth_headers)
    assert r.status_code == 200, r.text
    # El tenant de test (conftest) no siembra PUC/centros/periodos/parametros
    # via seed.py (eso solo corre en startup real) asi que en tenant 1 deben
    # ser 0 salvo lo que el propio test cree.
    assert r.json()["total_terceros"] == 0


@pytest.mark.asyncio
async def test_puc_update_toggle_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cuenta = PlanCuentas(
        codigo_puc="T2-1105", nombre="Caja T2",
        clase=ClaseCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEBITO, tenant_id=2,
    )
    db_session.add(cuenta)
    await db_session.commit()
    await db_session.refresh(cuenta)
    cuenta_id = cuenta.id
    await _al_tenant_default(db_session)

    r = await client.put(
        f"/api/v1/contabilidad/puc/{cuenta_id}", json={"nombre": "Hackeado"}, headers=auth_headers
    )
    assert r.status_code == 404

    r = await client.patch(f"/api/v1/contabilidad/puc/{cuenta_id}/toggle", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_centro_costo_update_toggle_otro_tenant_404(
    client: AsyncClient, auth_headers: dict, db_session
):
    await _en_tenant2(db_session)
    cc = CentroCosto(codigo="T2-CC01", nombre="CC T2", tipo="Marca", tenant_id=2)
    db_session.add(cc)
    await db_session.commit()
    await db_session.refresh(cc)
    cc_id = cc.id
    await _al_tenant_default(db_session)

    r = await client.put(
        f"/api/v1/contabilidad/centros-costo/{cc_id}", json={"nombre": "Hackeado"}, headers=auth_headers
    )
    assert r.status_code == 404

    r = await client.patch(f"/api/v1/contabilidad/centros-costo/{cc_id}/toggle", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_periodo_toggle_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    periodo = PeriodoContable(anio=2026, mes=3, periodo="2026-03", tenant_id=2)
    db_session.add(periodo)
    await db_session.commit()
    await db_session.refresh(periodo)
    periodo_id = periodo.id
    await _al_tenant_default(db_session)

    r = await client.patch(f"/api/v1/contabilidad/periodos/{periodo_id}/toggle", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason=(
        "Bug de ESQUEMA, no de query: UniqueConstraint('anio','mes') en "
        "PeriodoContable es global, sin tenant_id. El chequeo de duplicado "
        "en la app ya esta corregido (tenant_clause abajo), pero el INSERT "
        "mismo revienta con IntegrityError entre tenants. Requiere una "
        "migracion Alembic para hacer el constraint compuesto con "
        "tenant_id — mismo problema en PlanCuentas.codigo_puc, "
        "CentroCosto.codigo, Tercero.nit_cc, ParametroTributario.concepto, "
        "ParametroNomina.concepto, CuentaPorCobrar.numero_factura, "
        "CuentaPorPagar.numero_documento, Pago.numero_comprobante, "
        "Cotizacion.numero, DevolucionVenta.numero. "
        "Ver BITACORA.md 2026-07-24 — tarea de seguimiento separada, "
        "no forma parte de este fix de aislamiento a nivel de queries."
    ),
    strict=True,
)
async def test_periodo_duplicado_no_choca_entre_tenants(client: AsyncClient, auth_headers: dict, db_session):
    """Crear un periodo (anio, mes) en un tenant no debe bloquear que otro
    tenant cree el mismo (anio, mes) — el chequeo de duplicado global es un
    bug de aislamiento, no solo de UX."""
    await _en_tenant2(db_session)
    db_session.add(PeriodoContable(anio=2026, mes=4, periodo="2026-04", tenant_id=2))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.post(
        "/api/v1/contabilidad/periodos", json={"anio": 2026, "mes": 4}, headers=auth_headers
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_list_terceros_no_ve_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    db_session.add(Tercero(
        nit_cc="T2-SECRETO", razon_social="Tercero secreto", tipo=TipoTercero.CLIENTE, tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/contabilidad/terceros", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(t["nit_cc"] != "T2-SECRETO" for t in r.json())


@pytest.mark.asyncio
async def test_auxiliar_tercero_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    tercero = Tercero(
        nit_cc="T2-AUX", razon_social="Tercero aux T2", tipo=TipoTercero.CLIENTE, tenant_id=2,
    )
    db_session.add(tercero)
    await db_session.commit()
    await db_session.refresh(tercero)
    tercero_id = tercero.id
    await _al_tenant_default(db_session)

    r = await client.get(f"/api/v1/contabilidad/terceros/{tercero_id}/auxiliar", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_parametros_list_no_ve_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    db_session.add(ParametroTributario(concepto="T2-Secreto Tributario", tenant_id=2))
    db_session.add(ParametroNomina(concepto="T2-Secreto Nomina", tenant_id=2))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/contabilidad/parametros-tributarios", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(p["concepto"] != "T2-Secreto Tributario" for p in r.json())

    r = await client.get("/api/v1/contabilidad/parametros-nomina", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(p["concepto"] != "T2-Secreto Nomina" for p in r.json())


@pytest.mark.asyncio
async def test_parametros_update_toggle_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    pt = ParametroTributario(concepto="T2-PT", tenant_id=2)
    pn = ParametroNomina(concepto="T2-PN", tenant_id=2)
    db_session.add_all([pt, pn])
    await db_session.commit()
    await db_session.refresh(pt)
    await db_session.refresh(pn)
    pt_id, pn_id = pt.id, pn.id
    await _al_tenant_default(db_session)

    r = await client.put(
        f"/api/v1/contabilidad/parametros-tributarios/{pt_id}", json={"activo": False}, headers=auth_headers
    )
    assert r.status_code == 404
    r = await client.patch(f"/api/v1/contabilidad/parametros-tributarios/{pt_id}/toggle", headers=auth_headers)
    assert r.status_code == 404

    r = await client.put(
        f"/api/v1/contabilidad/parametros-nomina/{pn_id}", json={"activo": False}, headers=auth_headers
    )
    assert r.status_code == 404
    r = await client.patch(f"/api/v1/contabilidad/parametros-nomina/{pn_id}/toggle", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cartera_stats_no_cuenta_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    db_session.add(CuentaPorCobrar(
        numero_factura="T2-CXC-1", fecha_emision=date(2026, 1, 1),
        cliente_nit="T2", valor_factura=Decimal("999999"), tenant_id=2,
    ))
    db_session.add(CuentaPorPagar(
        numero_documento="T2-CXP-1", fecha=date(2026, 1, 1),
        proveedor_nit="T2", valor=Decimal("999999"), tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/contabilidad/cartera/stats", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_cxc"] == 0
    assert body["total_cxp"] == 0
    assert float(body["cxc_pendiente"]) == 0.0
    assert float(body["cxp_pendiente"]) == 0.0


@pytest.mark.asyncio
async def test_cxc_update_abonar_anular_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cxc = CuentaPorCobrar(
        numero_factura="T2-CXC-2", fecha_emision=date(2026, 1, 1),
        cliente_nit="T2", valor_factura=Decimal("1000"), tenant_id=2,
    )
    db_session.add(cxc)
    await db_session.commit()
    await db_session.refresh(cxc)
    cxc_id = cxc.id
    await _al_tenant_default(db_session)

    r = await client.put(
        f"/api/v1/contabilidad/cartera/cxc/{cxc_id}", json={"notas": "hackeado"}, headers=auth_headers
    )
    assert r.status_code == 404
    r = await client.post(
        f"/api/v1/contabilidad/cartera/cxc/{cxc_id}/abonar", json={"valor": 100}, headers=auth_headers
    )
    assert r.status_code == 404
    r = await client.patch(f"/api/v1/contabilidad/cartera/cxc/{cxc_id}/anular", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cxp_update_abonar_anular_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    cxp = CuentaPorPagar(
        numero_documento="T2-CXP-2", fecha=date(2026, 1, 1),
        proveedor_nit="T2", valor=Decimal("1000"), tenant_id=2,
    )
    db_session.add(cxp)
    await db_session.commit()
    await db_session.refresh(cxp)
    cxp_id = cxp.id
    await _al_tenant_default(db_session)

    r = await client.put(
        f"/api/v1/contabilidad/cartera/cxp/{cxp_id}", json={"concepto": "hackeado"}, headers=auth_headers
    )
    assert r.status_code == 404
    r = await client.post(
        f"/api/v1/contabilidad/cartera/cxp/{cxp_id}/abonar", json={"valor": 100}, headers=auth_headers
    )
    assert r.status_code == 404
    r = await client.patch(f"/api/v1/contabilidad/cartera/cxp/{cxp_id}/anular", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_pagos_no_ve_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    db_session.add(Pago(
        numero_comprobante="T2-RC-1", tipo=TipoPago.CXC, valor=Decimal("1"),
        saldo_anterior=Decimal("1"), saldo_nuevo=Decimal("0"), tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/contabilidad/cartera/pagos", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(p["numero_comprobante"] != "T2-RC-1" for p in r.json())


@pytest.mark.asyncio
async def test_anular_pago_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    pago = Pago(
        numero_comprobante="T2-RC-2", tipo=TipoPago.CXC, valor=Decimal("1"),
        saldo_anterior=Decimal("1"), saldo_nuevo=Decimal("0"), tenant_id=2,
    )
    db_session.add(pago)
    await db_session.commit()
    await db_session.refresh(pago)
    pago_id = pago.id
    await _al_tenant_default(db_session)

    r = await client.post(f"/api/v1/contabilidad/cartera/pagos/{pago_id}/anular", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_asientos_no_ve_otro_tenant(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    asiento = AsientoContable(
        fecha=date(2026, 1, 1), descripcion="Asiento secreto T2",
        documento_ref="T2-DOC-1", tenant_id=2,
    )
    db_session.add(asiento)
    await db_session.commit()
    await _al_tenant_default(db_session)

    r = await client.get("/api/v1/contabilidad/asientos", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(a["documento_ref"] != "T2-DOC-1" for a in r.json())


@pytest.mark.asyncio
async def test_get_asiento_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    await _en_tenant2(db_session)
    asiento = AsientoContable(
        fecha=date(2026, 1, 1), descripcion="Asiento secreto T2", tenant_id=2,
    )
    db_session.add(asiento)
    await db_session.commit()
    await db_session.refresh(asiento)
    asiento_id = asiento.id
    await _al_tenant_default(db_session)

    r = await client.get(f"/api/v1/contabilidad/asientos/{asiento_id}", headers=auth_headers)
    assert r.status_code == 404
