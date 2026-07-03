"""
15a: Anulación de abonos (Pago) — restaura saldo/estado del documento,
re-sincroniza la compra y genera el reverso contable.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1/contabilidad/cartera"


async def _cxc_con_abono(client, headers, valor_abono="400000.00"):
    cxc = (await client.post(
        f"{BASE}/cxc",
        json={"numero_factura": "FV-AP-001", "fecha_emision": "2026-07-01",
              "cliente_nit": "900900900", "nombre_cliente": "Cliente Anula SAS",
              "valor_factura": "1000000.00"},
        headers=headers,
    )).json()
    abono = (await client.post(
        f"{BASE}/cxc/{cxc['id']}/abonar", json={"valor": valor_abono}, headers=headers
    )).json()
    return cxc, abono["pago"]


@pytest.mark.asyncio
async def test_anular_abono_cxc_restaura_saldo_y_reversa_asiento(client: AsyncClient, auth_headers: dict):
    cxc, pago = await _cxc_con_abono(client, auth_headers)

    resp = await client.post(f"{BASE}/pagos/{pago['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    anulado = resp.json()
    assert anulado["anulado"] is True
    assert "[ANULADO]" in anulado["notas"]

    # El documento volvió a Pendiente con el saldo completo
    docs = (await client.get(f"{BASE}/cxc", headers=auth_headers)).json()
    doc = next(d for d in docs if d["id"] == cxc["id"])
    assert float(doc["saldo_pendiente"]) == 1000000.00
    assert doc["estado"] == "Pendiente"

    # El asiento del RC quedó reversado (2 asientos que netean a cero)
    asientos = (await client.get(
        f"/api/v1/contabilidad/asientos?documento_ref={pago['numero_comprobante']}",
        headers=auth_headers,
    )).json()
    assert len(asientos) == 2
    assert any(a["descripcion"].startswith("REVERSO") for a in asientos)

    # No se puede anular dos veces
    resp = await client.post(f"{BASE}/pagos/{pago['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.post(f"{BASE}/pagos/99999/anular", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_anular_uno_de_dos_abonos_deja_parcial(client: AsyncClient, auth_headers: dict):
    cxc, pago1 = await _cxc_con_abono(client, auth_headers, valor_abono="300000.00")
    abono2 = (await client.post(
        f"{BASE}/cxc/{cxc['id']}/abonar", json={"valor": "700000.00"}, headers=auth_headers
    )).json()
    # Documento quedó Pagado; anulamos el segundo abono → vuelve a Parcial
    resp = await client.post(
        f"{BASE}/pagos/{abono2['pago']['id']}/anular", headers=auth_headers
    )
    assert resp.status_code == 200

    docs = (await client.get(f"{BASE}/cxc", headers=auth_headers)).json()
    doc = next(d for d in docs if d["id"] == cxc["id"])
    assert doc["estado"] == "Parcial"
    assert float(doc["saldo_pendiente"]) == 700000.00

    # Y ahora se puede volver a abonar el saldo correcto
    resp = await client.post(
        f"{BASE}/cxc/{cxc['id']}/abonar", json={"valor": "700000.00"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["documento"]["estado"] == "Pagado"


@pytest.mark.asyncio
async def test_anular_abono_cxp_resincroniza_compra(client: AsyncClient, auth_headers: dict):
    # Compra confirmada → CxP → abono total → compra Pagado
    prov = (await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "800900900", "razon_social": "Proveedor Anula"},
        headers=auth_headers,
    )).json()
    compra = (await client.post(
        "/api/v1/compras/",
        json={"fecha": "2026-07-01", "proveedor_id": prov["id"],
              "detalles": [{"descripcion": "X", "cantidad": "1", "precio_unitario": "100000.00"}]},
        headers=auth_headers,
    )).json()
    await client.post(f"/api/v1/compras/{compra['id']}/confirmar", headers=auth_headers)
    cxp = next(
        c for c in (await client.get(f"{BASE}/cxp", headers=auth_headers)).json()
        if c["compra_id"] == compra["id"]
    )
    abono = (await client.post(
        f"{BASE}/cxp/{cxp['id']}/abonar", json={"valor": str(cxp["valor"])}, headers=auth_headers
    )).json()
    resp = await client.get(f"/api/v1/compras/{compra['id']}", headers=auth_headers)
    assert resp.json()["estado_pago"] == "Pagado"

    # Anular el pago → CxP Pendiente y compra Pendiente
    resp = await client.post(
        f"{BASE}/pagos/{abono['pago']['id']}/anular", headers=auth_headers
    )
    assert resp.status_code == 200, resp.text

    cxp2 = next(
        c for c in (await client.get(f"{BASE}/cxp", headers=auth_headers)).json()
        if c["id"] == cxp["id"]
    )
    assert cxp2["estado"] == "Pendiente"
    resp = await client.get(f"/api/v1/compras/{compra['id']}", headers=auth_headers)
    assert resp.json()["estado_pago"] == "Pendiente"


@pytest.mark.asyncio
async def test_anular_abono_bloqueado_con_periodo_cerrado(client: AsyncClient, auth_headers: dict):
    _, pago = await _cxc_con_abono(client, auth_headers)

    # Cerrar el período del mes actual (fecha del pago = hoy, hora Colombia)
    from app.core.time import bogota_now
    hoy = bogota_now()
    periodo = (await client.post(
        "/api/v1/contabilidad/periodos",
        json={"anio": hoy.year, "mes": hoy.month},
        headers=auth_headers,
    )).json()
    await client.patch(
        f"/api/v1/contabilidad/periodos/{periodo['id']}/toggle", headers=auth_headers
    )

    resp = await client.post(f"{BASE}/pagos/{pago['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400
    assert "CERRADO" in resp.json()["detail"]

    # El pago sigue vigente y el saldo intacto
    pagos = (await client.get(f"{BASE}/pagos", headers=auth_headers)).json()
    assert next(p for p in pagos if p["id"] == pago["id"])["anulado"] is False
