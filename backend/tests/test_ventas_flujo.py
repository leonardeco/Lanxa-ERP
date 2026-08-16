"""
Flujo completo del módulo de Ventas: CRUD de productos y clientes,
ciclo de vida del documento de venta (borrador → confirmada → anulada)
y sus efectos colaterales (inventario y CxC automática).
"""
import pytest
from httpx import AsyncClient


PRODUCTO_BASE = {
    "sku": "BIO-001",
    "nombre": "Biocida Superozono 20L",
    "marca": "Superozono",
    "precio_venta": "150000.00",
    "stock_actual": 50,
    "stock_minimo": 5,
}

CLIENTE_BASE = {
    "nit_cc": "900123456",
    "razon_social": "Distribuidora El Campo S.A.S.",
    "ciudad": "Armenia",
}


async def _crear_producto(client, headers, **overrides):
    resp = await client.post("/api/v1/ventas/productos", json={**PRODUCTO_BASE, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_cliente(client, headers, **overrides):
    resp = await client.post("/api/v1/ventas/clientes", json={**CLIENTE_BASE, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_venta(client, headers, cliente_id, producto_id, cantidad="2", precio="100000.00"):
    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": "2026-07-01",
            "cliente_id": cliente_id,
            "detalles": [{
                "producto_id": producto_id,
                "cantidad": cantidad,
                "precio_unitario": precio,
            }],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════
# Productos
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_producto_sku_duplicado_da_400(client: AsyncClient, auth_headers: dict):
    await _crear_producto(client, auth_headers)
    resp = await client.post("/api/v1/ventas/productos", json=PRODUCTO_BASE, headers=auth_headers)
    assert resp.status_code == 400
    assert "SKU" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_producto_get_update_delete(client: AsyncClient, auth_headers: dict):
    prod = await _crear_producto(client, auth_headers)

    # GET por id
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["sku"] == "BIO-001"

    # GET inexistente
    resp = await client.get("/api/v1/ventas/productos/99999", headers=auth_headers)
    assert resp.status_code == 404

    # UPDATE parcial
    resp = await client.put(
        f"/api/v1/ventas/productos/{prod['id']}",
        json={"precio_venta": "175000.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert float(resp.json()["precio_venta"]) == 175000.00

    # DELETE = soft delete (activo -> False)
    resp = await client.delete(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert resp.status_code == 200
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert resp.json()["activo"] is False

    # El filtro activo=true ya no lo lista
    resp = await client.get("/api/v1/ventas/productos?activo=true", headers=auth_headers)
    assert all(p["id"] != prod["id"] for p in resp.json())


# ══════════════════════════════════════════════════════════
# Clientes
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cliente_nit_duplicado_da_400(client: AsyncClient, auth_headers: dict):
    await _crear_cliente(client, auth_headers)
    resp = await client.post("/api/v1/ventas/clientes", json=CLIENTE_BASE, headers=auth_headers)
    assert resp.status_code == 400
    assert "NIT" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_cliente_get_update_delete(client: AsyncClient, auth_headers: dict):
    cli = await _crear_cliente(client, auth_headers)

    resp = await client.get(f"/api/v1/ventas/clientes/{cli['id']}", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.get("/api/v1/ventas/clientes/99999", headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.put(
        f"/api/v1/ventas/clientes/{cli['id']}",
        json={"ciudad": "Pereira"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ciudad"] == "Pereira"

    resp = await client.delete(f"/api/v1/ventas/clientes/{cli['id']}", headers=auth_headers)
    assert resp.status_code == 200
    resp = await client.get(f"/api/v1/ventas/clientes/{cli['id']}", headers=auth_headers)
    assert resp.json()["activo"] is False


# ══════════════════════════════════════════════════════════
# Documentos de venta — ciclo de vida
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_venta_sin_detalles_da_400(client: AsyncClient, auth_headers: dict):
    cli = await _crear_cliente(client, auth_headers)
    resp = await client.post(
        "/api/v1/ventas/",
        json={"fecha": "2026-07-01", "cliente_id": cli["id"], "detalles": []},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_venta_cliente_inexistente_da_404(client: AsyncClient, auth_headers: dict):
    prod = await _crear_producto(client, auth_headers)
    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": "2026-07-01",
            "cliente_id": 99999,
            "detalles": [{"producto_id": prod["id"], "cantidad": "1", "precio_unitario": "1000"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_venta_borrador_calcula_totales(client: AsyncClient, auth_headers: dict):
    cli = await _crear_cliente(client, auth_headers)
    prod = await _crear_producto(client, auth_headers)

    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="2", precio="100000.00")

    assert venta["estado"] == "Borrador"
    assert venta["numero"].startswith("LNX-V-")
    assert float(venta["subtotal"]) == 200000.00
    # IVA 19% por defecto
    assert float(venta["iva_total"]) == 38000.00
    assert float(venta["total"]) == 238000.00
    assert venta["cliente_razon_social"] == CLIENTE_BASE["razon_social"]
    assert len(venta["detalles"]) == 1


@pytest.mark.asyncio
async def test_confirmar_venta_descuenta_stock_y_crea_cxc(client: AsyncClient, auth_headers: dict):
    cli = await _crear_cliente(client, auth_headers)
    prod = await _crear_producto(client, auth_headers, stock_actual=10)
    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="4")

    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "Confirmada"

    # Stock descontado: 10 - 4 = 6
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 6.0

    # CxC generada automáticamente con el número de la venta
    resp = await client.get("/api/v1/contabilidad/cartera/cxc", headers=auth_headers)
    numeros = [c["numero_factura"] for c in resp.json()]
    assert venta["numero"] in numeros

    # No se puede confirmar dos veces
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_confirmar_venta_sin_stock_da_400(client: AsyncClient, auth_headers: dict):
    cli = await _crear_cliente(client, auth_headers)
    prod = await _crear_producto(client, auth_headers, stock_actual=1)
    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="5")

    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 400
    assert "Stock insuficiente" in resp.json()["detail"]

    # La venta sigue en borrador y el stock intacto
    resp = await client.get(f"/api/v1/ventas/{venta['id']}", headers=auth_headers)
    assert resp.json()["estado"] == "Borrador"
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 1.0


@pytest.mark.asyncio
async def test_anular_venta_confirmada_reversa_stock(client: AsyncClient, auth_headers: dict):
    cli = await _crear_cliente(client, auth_headers)
    prod = await _crear_producto(client, auth_headers, stock_actual=10)
    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="3")

    await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)

    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200

    # Stock restaurado: 10 - 3 + 3 = 10
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 10.0

    # Anular dos veces da 400
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_listar_ventas_con_filtro_estado(client: AsyncClient, auth_headers: dict):
    cli = await _crear_cliente(client, auth_headers)
    prod = await _crear_producto(client, auth_headers)
    await _crear_venta(client, auth_headers, cli["id"], prod["id"])

    resp = await client.get("/api/v1/ventas/?estado=Borrador", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get("/api/v1/ventas/?estado=Anulada", headers=auth_headers)
    assert resp.json() == []

    resp = await client.get("/api/v1/ventas/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_venta_con_retenciones_sugeridas(client: AsyncClient, auth_headers: dict):
    """Cliente que retiene IVA: la venta debe aplicar ReteIVA (15% del IVA) sola."""
    cli = await _crear_cliente(client, auth_headers, retiene_iva=True)
    prod = await _crear_producto(client, auth_headers)

    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="1", precio="1000000.00")

    # IVA = 190000; ReteIVA 15% = 28500
    assert float(venta["iva_total"]) == 190000.00
    assert float(venta["reteiva"]) == 28500.00
    assert float(venta["total"]) == 1000000.00 + 190000.00 - 28500.00


@pytest.mark.asyncio
async def test_dashboard_ventas_refleja_movimiento(client: AsyncClient, auth_headers: dict):
    cli = await _crear_cliente(client, auth_headers)
    prod = await _crear_producto(client, auth_headers, stock_actual=100)
    await _crear_venta(client, auth_headers, cli["id"], prod["id"])

    resp = await client.get("/api/v1/ventas/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_clientes_activos"] == 1
    assert data["total_productos_activos"] == 1
    assert isinstance(data["ventas_por_marca"], list)
