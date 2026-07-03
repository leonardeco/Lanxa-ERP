"""
Cartera CxC/CxP: creación, abonos con comprobante numerado (RC-/CE-),
anulación, validaciones de saldo e historial de pagos.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1/contabilidad/cartera"

CXC_BASE = {
    "numero_factura": "FV-001",
    "fecha_emision": "2026-06-01",
    "cliente_nit": "900111222",
    "nombre_cliente": "Cliente Cartera S.A.S.",
    "valor_factura": "1000000.00",
    "fecha_vencimiento": "2026-06-15",
}

CXP_BASE = {
    "numero_documento": "FC-001",
    "fecha": "2026-06-01",
    "proveedor_nit": "800333444",
    "razon_social": "Proveedor Cartera Ltda",
    "valor": "500000.00",
    "fecha_vencimiento": "2026-06-20",
}


async def _crear_cxc(client, headers, **overrides):
    resp = await client.post(f"{BASE}/cxc", json={**CXC_BASE, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_cxp(client, headers, **overrides):
    resp = await client.post(f"{BASE}/cxp", json={**CXP_BASE, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════
# CxC
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cxc_creacion_y_duplicado(client: AsyncClient, auth_headers: dict):
    cxc = await _crear_cxc(client, auth_headers)
    assert float(cxc["saldo_pendiente"]) == 1000000.00
    assert cxc["estado"] == "Pendiente"
    # La factura vence el 2026-06-15 y "hoy" es posterior → días vencido > 0
    assert cxc["dias_vencido"] > 0

    resp = await client.post(f"{BASE}/cxc", json=CXC_BASE, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_cxc_abono_parcial_y_total_generan_comprobantes(client: AsyncClient, auth_headers: dict):
    cxc = await _crear_cxc(client, auth_headers)

    # Abono parcial → estado Parcial, Recibo de Caja RC-0001
    resp = await client.post(
        f"{BASE}/cxc/{cxc['id']}/abonar",
        json={"valor": "400000.00", "notas": "Primer abono"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["documento"]["estado"] == "Parcial"
    assert float(data["documento"]["saldo_pendiente"]) == 600000.00
    assert data["pago"]["numero_comprobante"] == "RC-0001"
    assert float(data["pago"]["saldo_anterior"]) == 1000000.00
    assert float(data["pago"]["saldo_nuevo"]) == 600000.00

    # Abono por el resto → Pagado, RC-0002
    resp = await client.post(
        f"{BASE}/cxc/{cxc['id']}/abonar", json={"valor": "600000.00"}, headers=auth_headers
    )
    data = resp.json()
    assert data["documento"]["estado"] == "Pagado"
    assert data["pago"]["numero_comprobante"] == "RC-0002"

    # Sobre una CxC pagada no se puede abonar
    resp = await client.post(
        f"{BASE}/cxc/{cxc['id']}/abonar", json={"valor": "1.00"}, headers=auth_headers
    )
    assert resp.status_code == 400

    # Historial de pagos filtrado por cxc_id
    resp = await client.get(f"{BASE}/pagos?cxc_id={cxc['id']}", headers=auth_headers)
    comprobantes = [p["numero_comprobante"] for p in resp.json()]
    assert comprobantes == ["RC-0002", "RC-0001"]  # orden descendente por fecha


@pytest.mark.asyncio
async def test_cxc_abono_mayor_al_saldo_da_400(client: AsyncClient, auth_headers: dict):
    cxc = await _crear_cxc(client, auth_headers)
    resp = await client.post(
        f"{BASE}/cxc/{cxc['id']}/abonar", json={"valor": "2000000.00"}, headers=auth_headers
    )
    assert resp.status_code == 400
    assert "supera el saldo" in resp.json()["detail"]

    resp = await client.post(f"{BASE}/cxc/99999/abonar", json={"valor": "1.00"}, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cxc_update_y_anular(client: AsyncClient, auth_headers: dict):
    cxc = await _crear_cxc(client, auth_headers)

    resp = await client.put(
        f"{BASE}/cxc/{cxc['id']}", json={"marca": "Superozono"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["marca"] == "Superozono"

    resp = await client.put(f"{BASE}/cxc/99999", json={"marca": "X"}, headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.patch(f"{BASE}/cxc/{cxc['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["estado"] == "Anulado"
    # Anulada → días vencido siempre 0
    assert resp.json()["dias_vencido"] == 0

    resp = await client.patch(f"{BASE}/cxc/99999/anular", headers=auth_headers)
    assert resp.status_code == 404

    # Filtro por estado
    resp = await client.get(f"{BASE}/cxc?estado=Anulado", headers=auth_headers)
    assert len(resp.json()) == 1


# ══════════════════════════════════════════════════════════
# CxP
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cxp_ciclo_completo(client: AsyncClient, auth_headers: dict):
    cxp = await _crear_cxp(client, auth_headers)
    assert float(cxp["saldo_pendiente"]) == 500000.00

    resp = await client.post(f"{BASE}/cxp", json=CXP_BASE, headers=auth_headers)
    assert resp.status_code == 400  # duplicado

    # Abono parcial → Comprobante de Egreso CE-0001
    resp = await client.post(
        f"{BASE}/cxp/{cxp['id']}/abonar", json={"valor": "200000.00"}, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["documento"]["estado"] == "Parcial"
    assert data["pago"]["numero_comprobante"] == "CE-0001"

    # Abono que excede el saldo
    resp = await client.post(
        f"{BASE}/cxp/{cxp['id']}/abonar", json={"valor": "999999.00"}, headers=auth_headers
    )
    assert resp.status_code == 400

    # Pago total
    resp = await client.post(
        f"{BASE}/cxp/{cxp['id']}/abonar", json={"valor": "300000.00"}, headers=auth_headers
    )
    assert resp.json()["documento"]["estado"] == "Pagado"

    resp = await client.post(f"{BASE}/cxp/99999/abonar", json={"valor": "1.00"}, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cxp_update_y_anular(client: AsyncClient, auth_headers: dict):
    cxp = await _crear_cxp(client, auth_headers)

    resp = await client.put(
        f"{BASE}/cxp/{cxp['id']}", json={"concepto": "Materia prima"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["concepto"] == "Materia prima"

    resp = await client.put(f"{BASE}/cxp/99999", json={"concepto": "X"}, headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.patch(f"{BASE}/cxp/{cxp['id']}/anular", headers=auth_headers)
    assert resp.json()["estado"] == "Anulado"

    resp = await client.patch(f"{BASE}/cxp/99999/anular", headers=auth_headers)
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════
# Stats
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cartera_stats(client: AsyncClient, auth_headers: dict):
    await _crear_cxc(client, auth_headers)  # vencida (2026-06-15 < hoy)
    await _crear_cxp(client, auth_headers, fecha_vencimiento="2099-01-01")  # no vencida

    resp = await client.get(f"{BASE}/stats", headers=auth_headers)
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_cxc"] == 1
    assert stats["total_cxp"] == 1
    assert float(stats["cxc_pendiente"]) == 1000000.00
    assert float(stats["cxc_vencida"]) == 1000000.00
    assert float(stats["cxp_pendiente"]) == 500000.00
    assert float(stats["cxp_vencida"]) == 0.00
