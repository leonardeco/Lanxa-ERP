"""
Pruebas de las validaciones e integridad añadidas en la revisión de backend.
Cubren: validación de montos/cantidades/%, guard de sobreventa y numeración secuencial.
Cada test falla si la regresión reaparece.
"""

import pytest
from decimal import Decimal
from datetime import date
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

async def _crear_producto(client, auth_headers, sku, stock=100):
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": sku, "nombre": f"Prod {sku}", "marca": "Val-Test",
              "precio_venta": "50000.00", "tarifa_iva": "19.00",
              "stock_actual": stock, "stock_minimo": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_cliente(client, auth_headers, nit):
    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": nit, "razon_social": f"Cliente {nit}"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_venta(client, auth_headers, cliente_id, producto_id, cantidad="2.00"):
    return await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": cliente_id,
            "detalles": [{
                "producto_id": producto_id,
                "cantidad": cantidad,
                "precio_unitario": "50000.00",
                "descuento_porcentaje": "0.00",
                "iva_porcentaje": "19.00",
            }],
        },
        headers=auth_headers,
    )


# ══════════════════════════════════════════════════════════
# FASE 1 — Validación de montos, cantidades y porcentajes
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_abono_negativo_o_cero_es_rechazado(client: AsyncClient, auth_headers: dict):
    """Un abono <= 0 debe rechazarse con 422 (antes reducía el saldo y podía reabrir un pagado)."""
    cxc = await client.post(
        "/api/v1/contabilidad/cartera/cxc",
        json={"numero_factura": "FV-ABN-1", "fecha_emision": str(date.today()),
              "cliente_nit": "900", "nombre_cliente": "X", "valor_factura": "100000.00",
              "fecha_vencimiento": str(date.today())},
        headers=auth_headers,
    )
    assert cxc.status_code == 201, cxc.text
    cxc_id = cxc.json()["id"]

    for valor in ("-5000.00", "0.00"):
        r = await client.post(
            f"/api/v1/contabilidad/cartera/cxc/{cxc_id}/abonar",
            json={"valor": valor}, headers=auth_headers,
        )
        assert r.status_code == 422, f"valor={valor} debería ser rechazado, fue {r.status_code}"


@pytest.mark.asyncio
async def test_venta_con_cantidad_o_precio_invalido_rechazada(client: AsyncClient, auth_headers: dict):
    """cantidad<=0, precio<0 y descuento>100 deben dar 422."""
    prod = await _crear_producto(client, auth_headers, "VAL-1")
    cli = await _crear_cliente(client, auth_headers, "901")

    base = {"fecha": str(date.today()), "cliente_id": cli["id"]}

    def _linea(**over):
        linea = {"producto_id": prod["id"], "cantidad": "1.00",
                 "precio_unitario": "1000.00", "descuento_porcentaje": "0.00",
                 "iva_porcentaje": "19.00"}
        linea.update(over)
        return {**base, "detalles": [linea]}

    casos = [
        _linea(cantidad="0.00"),
        _linea(precio_unitario="-100.00"),
        _linea(descuento_porcentaje="150.00"),
        _linea(iva_porcentaje="200.00"),
    ]
    for payload in casos:
        r = await client.post("/api/v1/ventas/", json=payload, headers=auth_headers)
        assert r.status_code == 422, f"payload inválido aceptado: {payload} -> {r.status_code}"


# ══════════════════════════════════════════════════════════
# FASE 2 — Guard de sobreventa (stock insuficiente)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_confirmar_venta_sin_stock_suficiente_es_400(client: AsyncClient, auth_headers: dict):
    """Confirmar una venta cuya cantidad supera el stock debe dar 400, no dejar stock negativo."""
    prod = await _crear_producto(client, auth_headers, "VAL-STK", stock=5)
    cli = await _crear_cliente(client, auth_headers, "902")

    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="10.00")
    assert venta.status_code == 201, venta.text
    venta_id = venta.json()["id"]

    r = await client.post(f"/api/v1/ventas/{venta_id}/confirmar", headers=auth_headers)
    assert r.status_code == 400, r.text
    assert "insuficiente" in r.json()["detail"].lower()

    # El stock no debe haber cambiado
    prod_after = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert prod_after.json()["stock_actual"] == 5


@pytest.mark.asyncio
async def test_confirmar_venta_con_stock_descuenta_ok(client: AsyncClient, auth_headers: dict):
    """Camino feliz: con stock suficiente, confirmar descuenta el inventario."""
    prod = await _crear_producto(client, auth_headers, "VAL-STK2", stock=100)
    cli = await _crear_cliente(client, auth_headers, "903")

    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="10.00")
    venta_id = venta.json()["id"]

    r = await client.post(f"/api/v1/ventas/{venta_id}/confirmar", headers=auth_headers)
    assert r.status_code == 200, r.text

    prod_after = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert prod_after.json()["stock_actual"] == 90


# ══════════════════════════════════════════════════════════
# FASE 5 — Numeración secuencial y robusta
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_numeracion_ventas_es_secuencial(client: AsyncClient, auth_headers: dict):
    """Dos ventas consecutivas deben numerarse LNX-V-0001 y LNX-V-0002."""
    prod = await _crear_producto(client, auth_headers, "VAL-NUM")
    cli = await _crear_cliente(client, auth_headers, "904")

    v1 = await _crear_venta(client, auth_headers, cli["id"], prod["id"])
    v2 = await _crear_venta(client, auth_headers, cli["id"], prod["id"])
    assert v1.json()["numero"] == "LNX-V-0001"
    assert v2.json()["numero"] == "LNX-V-0002"


# ══════════════════════════════════════════════════════════
# BLOQUE 2 — Auto-CxC al confirmar una venta (espejo de compras→CxP)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_confirmar_venta_genera_cxc(client: AsyncClient, auth_headers: dict):
    """Al confirmar una venta debe crearse automáticamente una CxC por su total."""
    prod = await _crear_producto(client, auth_headers, "VAL-CXC", stock=100)
    cli = await _crear_cliente(client, auth_headers, "905")

    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="2.00")
    venta_json = venta.json()

    r = await client.post(f"/api/v1/ventas/{venta_json['id']}/confirmar", headers=auth_headers)
    assert r.status_code == 200, r.text

    cxc_list = (await client.get("/api/v1/contabilidad/cartera/cxc", headers=auth_headers)).json()
    match = [c for c in cxc_list if c["numero_factura"] == venta_json["numero"]]
    assert len(match) == 1, "Debe existir exactamente una CxC para la venta confirmada"
    assert str(match[0]["valor_factura"]) == str(venta_json["total"])


# ══════════════════════════════════════════════════════════
# BLOQUE 2 — Stock fraccionario (sin redondeo silencioso)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_stock_fraccionario_no_se_redondea(client: AsyncClient, auth_headers: dict):
    """Vender 2.5 de un stock de 10 debe dejar 7.5 exacto (antes redondeaba a entero)."""
    prod = await _crear_producto(client, auth_headers, "VAL-FRAC", stock=10)
    cli = await _crear_cliente(client, auth_headers, "906")

    venta = await _crear_venta(client, auth_headers, cli["id"], prod["id"], cantidad="2.50")
    venta_id = venta.json()["id"]

    r = await client.post(f"/api/v1/ventas/{venta_id}/confirmar", headers=auth_headers)
    assert r.status_code == 200, r.text

    prod_after = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(prod_after.json()["stock_actual"]) == 7.5


# ══════════════════════════════════════════════════════════
# BLOQUE 2 — Retenciones en ventas (híbrido: perfil del cliente + override)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cliente_no_retenedor_no_genera_retenciones(client: AsyncClient, auth_headers: dict):
    """Cliente por defecto (no agente retenedor) → sin retenciones."""
    prod = await _crear_producto(client, auth_headers, "RET-N")
    cli = await _crear_cliente(client, auth_headers, "910")  # sin flags
    v = (await _crear_venta(client, auth_headers, cli["id"], prod["id"])).json()
    assert Decimal(str(v["reteiva"])) == Decimal("0.00")
    assert Decimal(str(v["retefuente"])) == Decimal("0.00")
    assert Decimal(str(v["reteica"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_reteiva_se_sugiere_para_agente_retenedor(client: AsyncClient, auth_headers: dict):
    """Cliente con retiene_iva=True → reteiva = 15% del IVA (2 × 50.000, IVA 19.000 → 2.850)."""
    prod = await _crear_producto(client, auth_headers, "RET-IVA")
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "911", "razon_social": "Retenedor IVA", "retiene_iva": True},
        headers=auth_headers,
    )).json()
    v = (await _crear_venta(client, auth_headers, cli["id"], prod["id"])).json()
    assert Decimal(str(v["reteiva"])) == Decimal("2850.00")
    assert Decimal(str(v["total"])) == Decimal("116150.00")


@pytest.mark.asyncio
async def test_override_manual_de_retenciones_se_respeta(client: AsyncClient, auth_headers: dict):
    """Si el payload trae retenciones, mandan sobre la sugerencia automática."""
    prod = await _crear_producto(client, auth_headers, "RET-OVR")
    cli = await _crear_cliente(client, auth_headers, "912")
    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": cli["id"],
            "detalles": [{"producto_id": prod["id"], "cantidad": "2.00",
                          "precio_unitario": "50000.00", "descuento_porcentaje": "0.00",
                          "iva_porcentaje": "19.00"}],
            "retefuente": "1000.00",
            "reteica": "500.00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    v = resp.json()
    assert Decimal(str(v["retefuente"])) == Decimal("1000.00")
    assert Decimal(str(v["reteica"])) == Decimal("500.00")
    # total = 100.000 + 19.000 - 1.000 - 0 - 500 = 117.500
    assert Decimal(str(v["total"])) == Decimal("117500.00")


def test_calculo_dv_nit_algoritmo_dian():
    """14e: el DV calculado coincide con NITs reales conocidos."""
    from app.core.nit import calcular_dv

    # NIT de la propia empresa: 901841798-5 (ver .env.example / README)
    assert calcular_dv("901841798") == 5
    # NIT no numérico (cédula de extranjería) → no aplica
    assert calcular_dv("E-12345") is None


@pytest.mark.asyncio
async def test_dv_incorrecto_rechaza_cliente_y_proveedor(client, auth_headers):
    # DV equivocado → 422 con mensaje que dice el correcto
    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "901841798", "dv": "9", "razon_social": "DV Malo SAS"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "DV correcto es 5" in str(resp.json())

    # DV correcto → 201
    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "901841798", "dv": "5", "razon_social": "DV Bueno SAS"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Proveedor con DV equivocado → 422
    resp = await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "901841798", "dv": "0", "razon_social": "Prov DV Malo"},
        headers=auth_headers,
    )
    assert resp.status_code == 422

    # Sin DV → se acepta (campo opcional)
    resp = await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "800123456", "razon_social": "Prov Sin DV"},
        headers=auth_headers,
    )
    assert resp.status_code == 201


# ══════════════════════════════════════════════════════════
# 13a — Formato de email en cliente/proveedor (solo escritura)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_email_invalido_en_cliente_da_422(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900777001", "razon_social": "Email Malo SAS",
              "email": "esto no es un email"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_email_vacio_o_valido_en_cliente_ok(client: AsyncClient, auth_headers: dict):
    # '' se normaliza a None (el frontend envía cadena vacía)
    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900777002", "razon_social": "Sin Email SAS", "email": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["email"] is None

    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900777003", "razon_social": "Con Email SAS",
              "email": "compras@cliente.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "compras@cliente.com"

    # El update también valida
    cliente_id = resp.json()["id"]
    resp = await client.put(
        f"/api/v1/ventas/clientes/{cliente_id}",
        json={"email": "malo@"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_email_invalido_en_proveedor_da_422(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "800777001", "razon_social": "Proveedor Email Malo",
              "email": "sin-arroba"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ajuste_salida_no_deja_stock_negativo(client: AsyncClient, auth_headers: dict):
    """Revisión 2026-07-05: el ajuste manual era el único camino que permitía
    stock negativo en silencio."""
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "AJU-NEG", "nombre": "Producto Ajuste", "marca": "Superozono",
              "precio_venta": "1000", "stock_actual": 5},
        headers=auth_headers,
    )).json()

    # Salida mayor al stock → 400
    resp = await client.post(
        "/api/v1/inventario/ajustes",
        json={"producto_id": prod["id"], "tipo": "Salida", "cantidad": "8",
              "motivo": "prueba"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Stock insuficiente" in resp.json()["detail"]

    # Salida exacta del stock disponible → OK (queda en 0)
    resp = await client.post(
        "/api/v1/inventario/ajustes",
        json={"producto_id": prod["id"], "tipo": "Salida", "cantidad": "5",
              "motivo": "prueba"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 0.0
