"""
Flujo completo de Compras: CRUD de proveedores, ciclo de vida del
documento (borrador → confirmada → anulada), CxP automática, entradas
de inventario y sincronización de estado_pago vía abonos en cartera.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1/compras"

PROVEEDOR_BASE = {
    "nit_cc": "800555666",
    "razon_social": "Quimicos del Eje S.A.S.",
    "ciudad": "Pereira",
}


async def _crear_proveedor(client, headers, **overrides):
    resp = await client.post(f"{BASE}/proveedores", json={**PROVEEDOR_BASE, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_producto(client, headers, sku="MP-001"):
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": sku, "nombre": "Materia prima", "marca": "Genérica", "precio_venta": "0", "stock_actual": 0},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_compra(client, headers, proveedor_id, producto_id=None, cantidad="10", precio="50000.00"):
    resp = await client.post(
        f"{BASE}/",
        json={
            "fecha": "2026-07-01",
            "proveedor_id": proveedor_id,
            "detalles": [{
                "descripcion": "Insumo químico",
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
# Proveedores
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_proveedor_crud(client: AsyncClient, auth_headers: dict):
    prov = await _crear_proveedor(client, auth_headers)

    # NIT duplicado
    resp = await client.post(f"{BASE}/proveedores", json=PROVEEDOR_BASE, headers=auth_headers)
    assert resp.status_code == 400

    # UPDATE
    resp = await client.put(
        f"{BASE}/proveedores/{prov['id']}", json={"ciudad": "Manizales"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["ciudad"] == "Manizales"

    resp = await client.put(f"{BASE}/proveedores/99999", json={"ciudad": "X"}, headers=auth_headers)
    assert resp.status_code == 404

    # DELETE (soft) — devuelve 204 sin cuerpo
    resp = await client.delete(f"{BASE}/proveedores/{prov['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.delete(f"{BASE}/proveedores/99999", headers=auth_headers)
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════
# Documentos de compra
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_compra_validaciones_de_creacion(client: AsyncClient, auth_headers: dict):
    prov = await _crear_proveedor(client, auth_headers)

    # Sin detalles
    resp = await client.post(
        f"{BASE}/",
        json={"fecha": "2026-07-01", "proveedor_id": prov["id"], "detalles": []},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Proveedor inexistente
    resp = await client.post(
        f"{BASE}/",
        json={
            "fecha": "2026-07-01",
            "proveedor_id": 99999,
            "detalles": [{"descripcion": "X", "cantidad": "1", "precio_unitario": "100"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compra_borrador_calcula_totales(client: AsyncClient, auth_headers: dict):
    prov = await _crear_proveedor(client, auth_headers)
    compra = await _crear_compra(client, auth_headers, prov["id"], cantidad="10", precio="50000.00")

    assert compra["estado"] == "Borrador"
    assert compra["numero"].startswith("SOG-CP-")
    assert float(compra["subtotal"]) == 500000.00
    assert float(compra["iva_total"]) == 95000.00  # IVA 19% default
    assert float(compra["total"]) == 595000.00
    assert compra["proveedor_razon_social"] == PROVEEDOR_BASE["razon_social"]

    # GET por id y 404
    resp = await client.get(f"{BASE}/{compra['id']}", headers=auth_headers)
    assert resp.status_code == 200
    resp = await client.get(f"{BASE}/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_confirmar_compra_crea_cxp_y_entrada_inventario(client: AsyncClient, auth_headers: dict):
    prov = await _crear_proveedor(client, auth_headers)
    producto = await _crear_producto(client, auth_headers)
    compra = await _crear_compra(client, auth_headers, prov["id"], producto_id=producto["id"], cantidad="10")

    resp = await client.post(f"{BASE}/{compra['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["estado"] == "Confirmada"

    # Entrada automática: stock 0 → 10
    resp = await client.get(f"/api/v1/ventas/productos/{producto['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 10.0

    # CxP automática con el número de la compra y vinculada por compra_id
    resp = await client.get("/api/v1/contabilidad/cartera/cxp", headers=auth_headers)
    cxp = next(c for c in resp.json() if c["numero_documento"] == compra["numero"])
    assert cxp["compra_id"] == compra["id"]
    assert float(cxp["valor"]) == float(compra["total"])

    # No se puede confirmar dos veces
    resp = await client.post(f"{BASE}/{compra['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.post(f"{BASE}/99999/confirmar", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_abono_cxp_sincroniza_estado_pago_de_compra(client: AsyncClient, auth_headers: dict):
    prov = await _crear_proveedor(client, auth_headers)
    compra = await _crear_compra(client, auth_headers, prov["id"], cantidad="1", precio="100000.00")
    await client.post(f"{BASE}/{compra['id']}/confirmar", headers=auth_headers)

    resp = await client.get("/api/v1/contabilidad/cartera/cxp", headers=auth_headers)
    cxp = next(c for c in resp.json() if c["compra_id"] == compra["id"])

    # Abono parcial → compra queda "Parcial"
    await client.post(
        f"/api/v1/contabilidad/cartera/cxp/{cxp['id']}/abonar",
        json={"valor": "50000.00"},
        headers=auth_headers,
    )
    resp = await client.get(f"{BASE}/{compra['id']}", headers=auth_headers)
    assert resp.json()["estado_pago"] == "Parcial"

    # Pago del saldo → compra queda "Pagado"
    saldo = float(cxp["valor"]) - 50000.00
    await client.post(
        f"/api/v1/contabilidad/cartera/cxp/{cxp['id']}/abonar",
        json={"valor": str(saldo)},
        headers=auth_headers,
    )
    resp = await client.get(f"{BASE}/{compra['id']}", headers=auth_headers)
    assert resp.json()["estado_pago"] == "Pagado"


@pytest.mark.asyncio
async def test_anular_compra_confirmada_reversa_inventario(client: AsyncClient, auth_headers: dict):
    prov = await _crear_proveedor(client, auth_headers)
    producto = await _crear_producto(client, auth_headers, sku="MP-002")
    compra = await _crear_compra(client, auth_headers, prov["id"], producto_id=producto["id"], cantidad="8")

    await client.post(f"{BASE}/{compra['id']}/confirmar", headers=auth_headers)

    resp = await client.post(f"{BASE}/{compra['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["estado"] == "Anulada"
    assert resp.json()["estado_pago"] == "Anulado"

    # Reverso de la entrada: 0 + 8 - 8 = 0
    resp = await client.get(f"/api/v1/ventas/productos/{producto['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 0.0

    # Anular dos veces
    resp = await client.post(f"{BASE}/{compra['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.post(f"{BASE}/99999/anular", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_compras(client: AsyncClient, auth_headers: dict):
    prov = await _crear_proveedor(client, auth_headers)
    await _crear_compra(client, auth_headers, prov["id"])

    resp = await client.get(f"{BASE}/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_proveedores_activos"] == 1
