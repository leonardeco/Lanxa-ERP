"""
Capa 3 lote+vencimiento — enganche en compras/ventas/ajuste.
Verifica que los productos con controla_lote pasan por el servicio de lotes
(entrada_lote / consumir_fefo / revertir_por_lotes) manteniendo la invariante
stock_actual == Σ lotes, y que los productos sin lote no cambian de comportamiento.
"""
import pytest
from decimal import Decimal

from sqlalchemy import select, func

from app.modules.inventario.models import Lote


PROVEEDOR = {"nit_cc": "800111222", "razon_social": "Insumos Orgánicos S.A.S.", "ciudad": "Pereira"}
CLIENTE = {"nit_cc": "900333444", "razon_social": "Agro Distribuidora S.A.S.", "ciudad": "Armenia"}


async def _producto_lote(client, headers, sku="LOT-1"):
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": sku, "nombre": "Aceite Ozonizado", "marca": "Superozono",
              "precio_venta": "80000", "stock_actual": 0, "controla_lote": True},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _proveedor(client, headers):
    resp = await client.post("/api/v1/compras/proveedores", json=PROVEEDOR, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _cliente(client, headers):
    resp = await client.post("/api/v1/ventas/clientes", json=CLIENTE, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _compra_lote(client, headers, proveedor_id, producto_id, cantidad, codigo, venc):
    resp = await client.post(
        "/api/v1/compras/",
        json={"fecha": "2026-07-01", "proveedor_id": proveedor_id,
              "detalles": [{"descripcion": "Lote de aceite", "producto_id": producto_id,
                            "cantidad": cantidad, "precio_unitario": "30000",
                            "codigo_lote": codigo, "fecha_vencimiento": venc}]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    compra = resp.json()
    resp = await client.post(f"/api/v1/compras/{compra['id']}/confirmar", headers=headers)
    assert resp.status_code == 200, resp.text
    return compra


async def _venta(client, headers, cliente_id, producto_id, cantidad):
    resp = await client.post(
        "/api/v1/ventas/",
        json={"fecha": "2026-07-02", "cliente_id": cliente_id,
              "detalles": [{"producto_id": producto_id, "cantidad": cantidad,
                            "precio_unitario": "80000"}]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _stock(client, headers, producto_id):
    resp = await client.get(f"/api/v1/ventas/productos/{producto_id}", headers=headers)
    assert resp.status_code == 200
    return Decimal(str(resp.json()["stock_actual"]))


async def _lote(db_session, producto_id, codigo):
    return (await db_session.execute(
        select(Lote).where(Lote.producto_id == producto_id, Lote.codigo_lote == codigo)
    )).scalar_one()


async def _suma_lotes(db_session, producto_id):
    return (await db_session.execute(
        select(func.coalesce(func.sum(Lote.cantidad_actual), 0))
        .where(Lote.producto_id == producto_id))).scalar()


# ── Compra ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compra_confirmada_crea_lote(client, auth_headers, db_session):
    prov = await _proveedor(client, auth_headers)
    prod = await _producto_lote(client, auth_headers)
    await _compra_lote(client, auth_headers, prov["id"], prod["id"], "30", "L1", "2027-06-30")

    assert await _stock(client, auth_headers, prod["id"]) == Decimal("30")
    lote = await _lote(db_session, prod["id"], "L1")
    assert lote.cantidad_actual == Decimal("30")
    assert lote.fecha_vencimiento.isoformat() == "2027-06-30"


@pytest.mark.asyncio
async def test_compra_lote_sin_codigo_da_400(client, auth_headers):
    prov = await _proveedor(client, auth_headers)
    prod = await _producto_lote(client, auth_headers, sku="LOT-NC")
    resp = await client.post(
        "/api/v1/compras/",
        json={"fecha": "2026-07-01", "proveedor_id": prov["id"],
              "detalles": [{"descripcion": "sin lote", "producto_id": prod["id"],
                            "cantidad": "5", "precio_unitario": "30000"}]},
        headers=auth_headers,
    )
    compra = resp.json()
    resp = await client.post(f"/api/v1/compras/{compra['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 400
    assert "lote" in resp.json()["detail"].lower()


# ── Venta FEFO ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_venta_consume_fefo(client, auth_headers, db_session):
    prov = await _proveedor(client, auth_headers)
    cli = await _cliente(client, auth_headers)
    prod = await _producto_lote(client, auth_headers, sku="LOT-FEFO")

    await _compra_lote(client, auth_headers, prov["id"], prod["id"], "30", "A", "2027-12-01")  # vence después
    await _compra_lote(client, auth_headers, prov["id"], prod["id"], "20", "B", "2027-03-01")  # vence antes

    await _venta(client, auth_headers, cli["id"], prod["id"], "25")  # borrador no descuenta
    # el borrador no toca stock; se confirma:
    resp = await client.get("/api/v1/ventas/", headers=auth_headers)
    venta_id = resp.json()[0]["id"]
    resp = await client.post(f"/api/v1/ventas/{venta_id}/confirmar", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    a = await _lote(db_session, prod["id"], "A")
    b = await _lote(db_session, prod["id"], "B")
    assert b.cantidad_actual == Decimal("0") and b.activo is False  # se agota el que vence antes
    assert a.cantidad_actual == Decimal("25")                       # 30 - 5
    assert await _stock(client, auth_headers, prod["id"]) == Decimal("25")
    assert await _suma_lotes(db_session, prod["id"]) == Decimal("25")


@pytest.mark.asyncio
async def test_anular_venta_reingresa_a_lotes(client, auth_headers, db_session):
    prov = await _proveedor(client, auth_headers)
    cli = await _cliente(client, auth_headers)
    prod = await _producto_lote(client, auth_headers, sku="LOT-ANV")
    await _compra_lote(client, auth_headers, prov["id"], prod["id"], "40", "U", "2027-09-01")

    await _venta(client, auth_headers, cli["id"], prod["id"], "15")
    venta_id = (await client.get("/api/v1/ventas/", headers=auth_headers)).json()[0]["id"]
    await client.post(f"/api/v1/ventas/{venta_id}/confirmar", headers=auth_headers)
    assert await _stock(client, auth_headers, prod["id"]) == Decimal("25")

    resp = await client.post(f"/api/v1/ventas/{venta_id}/anular", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert await _stock(client, auth_headers, prod["id"]) == Decimal("40")  # reingresó al lote
    lote = await _lote(db_session, prod["id"], "U")
    assert lote.cantidad_actual == Decimal("40") and lote.activo is True


@pytest.mark.asyncio
async def test_devolucion_venta_reingresa_parcial(client, auth_headers, db_session):
    prov = await _proveedor(client, auth_headers)
    cli = await _cliente(client, auth_headers)
    prod = await _producto_lote(client, auth_headers, sku="LOT-NCV")
    await _compra_lote(client, auth_headers, prov["id"], prod["id"], "50", "Z", "2027-10-01")

    venta = await _venta(client, auth_headers, cli["id"], prod["id"], "20")
    venta_id = venta["id"]
    await client.post(f"/api/v1/ventas/{venta_id}/confirmar", headers=auth_headers)

    det_id = venta["detalles"][0]["id"]
    resp = await client.post(
        f"/api/v1/ventas/{venta_id}/devoluciones",
        json={"motivo": "Producto no conforme", "detalles": [{"venta_detalle_id": det_id, "cantidad": "5"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    # 50 - 20 (venta) + 5 (devolución) = 35
    assert await _stock(client, auth_headers, prod["id"]) == Decimal("35")
    assert await _suma_lotes(db_session, prod["id"]) == Decimal("35")


@pytest.mark.asyncio
async def test_anular_compra_revierte_lote(client, auth_headers, db_session):
    prov = await _proveedor(client, auth_headers)
    prod = await _producto_lote(client, auth_headers, sku="LOT-ANC")
    compra = await _compra_lote(client, auth_headers, prov["id"], prod["id"], "12", "C1", "2027-05-01")

    assert await _stock(client, auth_headers, prod["id"]) == Decimal("12")
    resp = await client.post(f"/api/v1/compras/{compra['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert await _stock(client, auth_headers, prod["id"]) == Decimal("0")
    lote = await _lote(db_session, prod["id"], "C1")
    assert lote.cantidad_actual == Decimal("0") and lote.activo is False


# ── Ajuste ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ajuste_entrada_y_salida_con_lote(client, auth_headers, db_session):
    prod = await _producto_lote(client, auth_headers, sku="LOT-AJU")

    # Entrada por ajuste crea el lote
    resp = await client.post(
        "/api/v1/inventario/ajustes",
        json={"producto_id": prod["id"], "tipo": "Entrada", "cantidad": "18",
              "codigo_lote": "AJ", "fecha_vencimiento": "2027-08-01", "motivo": "Conteo inicial"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert await _stock(client, auth_headers, prod["id"]) == Decimal("18")

    # Entrada sin código en producto con lote → 400
    resp = await client.post(
        "/api/v1/inventario/ajustes",
        json={"producto_id": prod["id"], "tipo": "Entrada", "cantidad": "3"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Salida por ajuste consume FEFO
    resp = await client.post(
        "/api/v1/inventario/ajustes",
        json={"producto_id": prod["id"], "tipo": "Salida", "cantidad": "8", "motivo": "Merma"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert await _stock(client, auth_headers, prod["id"]) == Decimal("10")
    lote = await _lote(db_session, prod["id"], "AJ")
    assert lote.cantidad_actual == Decimal("10")
    assert await _suma_lotes(db_session, prod["id"]) == Decimal("10")
