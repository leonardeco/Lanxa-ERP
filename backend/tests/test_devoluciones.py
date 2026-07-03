"""
Devoluciones: nota crédito (ventas) y devolución a proveedor (compras).
Verifica inventario, cartera y asiento contable en cada flujo.
"""
import pytest
from httpx import AsyncClient


async def _venta_confirmada(client, headers):
    """Cliente + producto (stock 50) + venta de 10 und a $10.000 confirmada."""
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900111333", "razon_social": "Cliente Dev SAS"},
        headers=headers,
    )).json()
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "DEV-001", "nombre": "Biocida Dev", "marca": "Superozono",
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
    venta = resp.json()
    return venta, prod


async def _compra_confirmada(client, headers):
    prov = (await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "800111333", "razon_social": "Proveedor Dev"},
        headers=headers,
    )).json()
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "DEV-C01", "nombre": "Insumo Dev", "marca": "Genérica",
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


# ══════════════════════════════════════════════════════════
# Nota crédito (ventas)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_nota_credito_parcial_completa(client: AsyncClient, auth_headers: dict):
    venta, prod = await _venta_confirmada(client, auth_headers)
    detalle_id = venta["detalles"][0]["id"]

    # Devolver 4 de 10 unidades
    resp = await client.post(
        f"/api/v1/ventas/{venta['id']}/devoluciones",
        json={"motivo": "Producto averiado en transporte",
              "detalles": [{"venta_detalle_id": detalle_id, "cantidad": "4"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    nc = resp.json()
    assert nc["numero"] == "NC-0001"
    assert float(nc["subtotal"]) == 40000.0          # 4 × 10.000
    assert float(nc["iva_total"]) == 7600.0          # 19%
    assert float(nc["total"]) == 47600.0

    # Inventario: 50 - 10 (venta) + 4 (devolución) = 44
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 44.0

    # CxC reducida: 119.000 - 47.600 = 71.400 pendiente
    cxc = next(
        c for c in (await client.get("/api/v1/contabilidad/cartera/cxc", headers=auth_headers)).json()
        if c["numero_factura"] == venta["numero"]
    )
    assert float(cxc["saldo_pendiente"]) == 71400.0
    assert "[NC] NC-0001" in cxc["notas"]

    # Asiento balanceado: DB 417501 + 240801 / CR 130505
    asientos = (await client.get(
        "/api/v1/contabilidad/asientos?documento_ref=NC-0001", headers=auth_headers
    )).json()
    assert len(asientos) == 1
    cuentas = {m["cuenta_codigo"]: (float(m["debito"]), float(m["credito"]))
               for m in asientos[0]["movimientos"]}
    assert cuentas["417501"] == (40000.0, 0.0)
    assert cuentas["240801"] == (7600.0, 0.0)
    assert cuentas["130505"] == (0.0, 47600.0)

    # El P&L neto refleja la devolución: ingresos 100.000 - 40.000 = 60.000
    pl = (await client.get(
        "/api/v1/reportes/estado-resultados?fecha_desde=2026-07-01&fecha_hasta=2026-07-31",
        headers=auth_headers,
    )).json()
    assert float(pl["ingresos"]["total"]) == 60000.0


@pytest.mark.asyncio
async def test_nota_credito_no_excede_lo_vendido(client: AsyncClient, auth_headers: dict):
    venta, _ = await _venta_confirmada(client, auth_headers)
    detalle_id = venta["detalles"][0]["id"]

    # Primera devolución de 8
    await client.post(
        f"/api/v1/ventas/{venta['id']}/devoluciones",
        json={"motivo": "Avería parcial",
              "detalles": [{"venta_detalle_id": detalle_id, "cantidad": "8"}]},
        headers=auth_headers,
    )
    # Segunda por 5 → excede lo restante (2) → 400
    resp = await client.post(
        f"/api/v1/ventas/{venta['id']}/devoluciones",
        json={"motivo": "Otra avería",
              "detalles": [{"venta_detalle_id": detalle_id, "cantidad": "5"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "máximo 2" in resp.json()["detail"]

    # Por 2 sí funciona (devolución total acumulada)
    resp = await client.post(
        f"/api/v1/ventas/{venta['id']}/devoluciones",
        json={"motivo": "Resto averiado",
              "detalles": [{"venta_detalle_id": detalle_id, "cantidad": "2"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["numero"] == "NC-0002"

    # Listado por venta
    resp = await client.get(f"/api/v1/ventas/{venta['id']}/devoluciones", headers=auth_headers)
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_nota_credito_solo_ventas_confirmadas(client: AsyncClient, auth_headers: dict):
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900222444", "razon_social": "Borrador SAS"},
        headers=auth_headers,
    )).json()
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "DEV-B01", "nombre": "P", "marca": "M", "precio_venta": "100"},
        headers=auth_headers,
    )).json()
    venta = (await client.post(
        "/api/v1/ventas/",
        json={"fecha": "2026-07-01", "cliente_id": cli["id"],
              "detalles": [{"producto_id": prod["id"], "cantidad": "1", "precio_unitario": "100"}]},
        headers=auth_headers,
    )).json()

    resp = await client.post(
        f"/api/v1/ventas/{venta['id']}/devoluciones",
        json={"motivo": "No aplica",
              "detalles": [{"venta_detalle_id": venta["detalles"][0]["id"], "cantidad": "1"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    resp = await client.post(
        "/api/v1/ventas/99999/devoluciones",
        json={"motivo": "No existe", "detalles": [{"venta_detalle_id": 1, "cantidad": "1"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════
# Devolución a proveedor (compras)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_devolucion_compra_completa(client: AsyncClient, auth_headers: dict):
    compra, prod = await _compra_confirmada(client, auth_headers)
    detalle_id = compra["detalles"][0]["id"]

    # Devolver 5 de 20 unidades
    resp = await client.post(
        f"/api/v1/compras/{compra['id']}/devoluciones",
        json={"motivo": "Lote defectuoso",
              "detalles": [{"compra_detalle_id": detalle_id, "cantidad": "5"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    nd = resp.json()
    assert nd["numero"] == "ND-0001"
    assert float(nd["subtotal"]) == 25000.0   # 5 × 5.000
    assert float(nd["total"]) == 29750.0      # + IVA 19%

    # Inventario: 0 + 20 (compra) - 5 (devolución) = 15
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 15.0

    # CxP reducida: 119.000 - 29.750 = 89.250
    cxp = next(
        c for c in (await client.get("/api/v1/contabilidad/cartera/cxp", headers=auth_headers)).json()
        if c["compra_id"] == compra["id"]
    )
    assert float(cxp["saldo_pendiente"]) == 89250.0

    # Asiento: DB 220501 / CR 143501 + 240802
    asientos = (await client.get(
        "/api/v1/contabilidad/asientos?documento_ref=ND-0001", headers=auth_headers
    )).json()
    cuentas = {m["cuenta_codigo"]: (float(m["debito"]), float(m["credito"]))
               for m in asientos[0]["movimientos"]}
    assert cuentas["220501"] == (29750.0, 0.0)
    assert cuentas["143501"] == (0.0, 25000.0)
    assert cuentas["240802"] == (0.0, 4750.0)

    # El balance sigue cuadrado tras la devolución
    bg = (await client.get(
        "/api/v1/reportes/balance-general?fecha_corte=2026-07-31", headers=auth_headers
    )).json()
    assert bg["cuadrado"] is True


@pytest.mark.asyncio
async def test_devolucion_compra_valida_stock(client: AsyncClient, auth_headers: dict):
    """Si la mercancía comprada ya se vendió, no se puede devolver al proveedor."""
    compra, prod = await _compra_confirmada(client, auth_headers)  # stock queda en 20
    detalle_id = compra["detalles"][0]["id"]

    # Vender 18 de las 20 unidades
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900333555", "razon_social": "Compra Casi Todo SAS"},
        headers=auth_headers,
    )).json()
    venta = (await client.post(
        "/api/v1/ventas/",
        json={"fecha": "2026-07-02", "cliente_id": cli["id"],
              "detalles": [{"producto_id": prod["id"], "cantidad": "18",
                            "precio_unitario": "8000"}]},
        headers=auth_headers,
    )).json()
    await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)

    # Quedan 2 en stock: devolver 5 al proveedor debe fallar
    resp = await client.post(
        f"/api/v1/compras/{compra['id']}/devoluciones",
        json={"motivo": "Defecto",
              "detalles": [{"compra_detalle_id": detalle_id, "cantidad": "5"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Stock insuficiente" in resp.json()["detail"]
