"""
BUG-007/008 (revisión 2026-07-05): la anulación de ventas/compras debe
sincronizar la cartera y protegerse de flujos cruzados:
- anular una venta/compra anula también su CxC/CxP,
- no se puede anular si hay abonos (primero se anulan los pagos),
- no se puede anular si hay devoluciones (el stock ya fue ajustado por la NC/ND).
"""
import pytest
from httpx import AsyncClient


async def _venta_confirmada(client, headers, nit="900321654", sku="ANU-001"):
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": nit, "razon_social": f"Cliente Anulación {nit}"},
        headers=headers,
    )).json()
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": sku, "nombre": "Biocida Anulación", "marca": "Superozono",
              "precio_venta": "10000", "stock_actual": 50},
        headers=headers,
    )).json()
    venta = (await client.post(
        "/api/v1/ventas/",
        json={"fecha": "2026-07-01", "cliente_id": cli["id"],
              "detalles": [{"producto_id": prod["id"], "cantidad": "10",
                            "precio_unitario": "10000.00"}]},
        headers=headers,
    )).json()
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json(), prod


async def _cxc_de(client, headers, numero_factura):
    todas = (await client.get("/api/v1/contabilidad/cartera/cxc", headers=headers)).json()
    return next(c for c in todas if c["numero_factura"] == numero_factura)


@pytest.mark.asyncio
async def test_anular_venta_anula_su_cxc(client: AsyncClient, auth_headers: dict):
    venta, prod = await _venta_confirmada(client, auth_headers)

    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    cxc = await _cxc_de(client, auth_headers, venta["numero"])
    assert cxc["estado"] == "Anulado"
    assert "[ANULADA]" in cxc["notas"]

    # El stock regresó al valor original
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 50.0


@pytest.mark.asyncio
async def test_anular_venta_con_abonos_bloqueada(client: AsyncClient, auth_headers: dict):
    venta, _ = await _venta_confirmada(client, auth_headers, nit="900321655", sku="ANU-002")
    cxc = await _cxc_de(client, auth_headers, venta["numero"])

    # Abono parcial
    resp = await client.post(
        f"/api/v1/contabilidad/cartera/cxc/{cxc['id']}/abonar",
        json={"valor": "50000.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text

    # Con plata recibida no se puede anular la venta
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400
    assert "abonos" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_anular_venta_con_nota_credito_bloqueada(client: AsyncClient, auth_headers: dict):
    venta, prod = await _venta_confirmada(client, auth_headers, nit="900321656", sku="ANU-003")

    # NC parcial: devuelve 4 de 10 (stock 50-10+4 = 44)
    detalle_id = venta["detalles"][0]["id"]
    resp = await client.post(
        f"/api/v1/ventas/{venta['id']}/devoluciones",
        json={"motivo": "Producto averiado",
              "detalles": [{"venta_detalle_id": detalle_id, "cantidad": "4"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    # Anular ahora duplicaría el reingreso → bloqueado
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400
    assert "notas crédito" in resp.json()["detail"]

    # El stock quedó exactamente como lo dejó la devolución
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 44.0


# ── Espejo en compras ─────────────────────────────────────

async def _compra_confirmada(client, headers, nit="800321654", sku="ANU-C01"):
    prov = (await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": nit, "razon_social": f"Proveedor Anulación {nit}"},
        headers=headers,
    )).json()
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": sku, "nombre": "Insumo Anulación", "marca": "Genérica",
              "precio_venta": "0", "stock_actual": 0},
        headers=headers,
    )).json()
    compra = (await client.post(
        "/api/v1/compras/",
        json={"fecha": "2026-07-01", "proveedor_id": prov["id"],
              "detalles": [{"descripcion": "Insumo", "producto_id": prod["id"],
                            "cantidad": "20", "precio_unitario": "5000.00"}]},
        headers=headers,
    )).json()
    resp = await client.post(f"/api/v1/compras/{compra['id']}/confirmar", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json(), prod


@pytest.mark.asyncio
async def test_anular_compra_anula_su_cxp(client: AsyncClient, auth_headers: dict):
    compra, _ = await _compra_confirmada(client, auth_headers)

    resp = await client.post(f"/api/v1/compras/{compra['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    cxps = (await client.get("/api/v1/contabilidad/cartera/cxp", headers=auth_headers)).json()
    cxp = next(p for p in cxps if p["numero_documento"] == compra["numero"])
    assert cxp["estado"] == "Anulado"


@pytest.mark.asyncio
async def test_anular_compra_con_devolucion_bloqueada(client: AsyncClient, auth_headers: dict):
    compra, _ = await _compra_confirmada(client, auth_headers, nit="800321655", sku="ANU-C02")

    detalle_id = compra["detalles"][0]["id"]
    resp = await client.post(
        f"/api/v1/compras/{compra['id']}/devoluciones",
        json={"motivo": "Lote defectuoso",
              "detalles": [{"compra_detalle_id": detalle_id, "cantidad": "5"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post(f"/api/v1/compras/{compra['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400
    assert "devoluciones" in resp.json()["detail"]
