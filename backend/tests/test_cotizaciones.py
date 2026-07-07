"""
Cotizaciones (COT-####): flujo Borrador→Enviada→Aprobada/Rechazada→Convertida.
Una cotización no toca inventario ni contabilidad; al convertirla nace una
venta en Borrador que sigue el flujo normal.
"""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def _cliente_y_producto(client, headers):
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900222444", "razon_social": "Cliente Cotiza SAS"},
        headers=headers,
    )).json()
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "COT-P01", "nombre": "Biocida Cotizado", "marca": "Superozono",
              "precio_venta": "20000", "stock_actual": 30},
        headers=headers,
    )).json()
    return cli, prod


async def _crear_cotizacion(client, headers, cli, prod, fecha=None, vigencia=15):
    resp = await client.post(
        "/api/v1/ventas/cotizaciones",
        json={"fecha": (fecha or date.today()).isoformat(),
              "vigencia_dias": vigencia,
              "cliente_id": cli["id"],
              "vendedor": "Leonardo",
              "detalles": [{"producto_id": prod["id"], "cantidad": "5",
                            "precio_unitario": "20000.00",
                            "descuento_porcentaje": "10"}]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_crear_cotizacion_calcula_totales(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)

    assert cot["numero"] == "COT-0001"
    assert cot["estado"] == "Borrador"
    assert cot["vencida"] is False
    # 5 × 20.000 = 100.000; -10% desc = 90.000 base; IVA 19% = 17.100
    assert float(cot["subtotal"]) == 100000.0
    assert float(cot["descuento_total"]) == 10000.0
    assert float(cot["base_gravable"]) == 90000.0
    assert float(cot["iva_total"]) == 17100.0
    assert float(cot["total"]) == 107100.0
    assert cot["cliente_razon_social"] == "Cliente Cotiza SAS"
    assert cot["detalles"][0]["producto_sku"] == "COT-P01"
    # Vigencia: fecha + 15 días
    esperado = date.today() + timedelta(days=15)
    assert cot["fecha_vencimiento"] == esperado.isoformat()

    # No tocó inventario
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 30.0


@pytest.mark.asyncio
async def test_flujo_completo_hasta_venta(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)

    # Borrador → Enviada → Aprobada
    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/enviar", headers=auth_headers)
    assert resp.status_code == 200 and resp.json()["estado"] == "Enviada"
    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/aprobar", headers=auth_headers)
    assert resp.status_code == 200 and resp.json()["estado"] == "Aprobada"

    # Aprobada → Convertida (crea venta en Borrador)
    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/convertir", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    convertida = resp.json()
    assert convertida["estado"] == "Convertida"
    assert convertida["venta_id"] is not None
    assert convertida["venta_numero"] == "SOG-V-0001"

    venta = (await client.get(
        f"/api/v1/ventas/{convertida['venta_id']}", headers=auth_headers)).json()
    assert venta["estado"] == "Borrador"
    assert float(venta["total"]) == float(cot["total"])
    assert "Generada desde cotización COT-0001" in venta["observaciones"]
    # La venta en borrador aún no descuenta stock
    resp = await client.get(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)
    assert float(resp.json()["stock_actual"]) == 30.0

    # No se puede convertir dos veces
    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/convertir", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_rechazo_con_motivo(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)

    resp = await client.post(
        f"/api/v1/ventas/cotizaciones/{cot['id']}/rechazar",
        json={"motivo": "Precio fuera de presupuesto"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "Rechazada"
    assert body["motivo_rechazo"] == "Precio fuera de presupuesto"

    # Rechazada no se puede aprobar ni convertir
    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/aprobar", headers=auth_headers)
    assert resp.status_code == 400
    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/convertir", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_transiciones_invalidas(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)

    # Convertir directo desde Borrador → 400 (falta aprobación)
    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/convertir", headers=auth_headers)
    assert resp.status_code == 400

    # Enviar dos veces → 400
    await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/enviar", headers=auth_headers)
    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/enviar", headers=auth_headers)
    assert resp.status_code == 400

    # 404 para IDs inexistentes
    resp = await client.get("/api/v1/ventas/cotizaciones/9999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cotizacion_vencida_no_se_aprueba(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    # Cotización fechada hace 30 días con vigencia de 10 → vencida hace 20
    vieja = date.today() - timedelta(days=30)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod, fecha=vieja, vigencia=10)
    assert cot["vencida"] is True

    resp = await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/aprobar", headers=auth_headers)
    assert resp.status_code == 400
    assert "venció" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_validaciones_de_creacion(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)

    # Sin detalles → 422 (min_length=1 en el schema)
    resp = await client.post(
        "/api/v1/ventas/cotizaciones",
        json={"fecha": date.today().isoformat(), "cliente_id": cli["id"], "detalles": []},
        headers=auth_headers,
    )
    assert resp.status_code == 422

    # Cliente inexistente → 404
    resp = await client.post(
        "/api/v1/ventas/cotizaciones",
        json={"fecha": date.today().isoformat(), "cliente_id": 9999,
              "detalles": [{"producto_id": prod["id"], "cantidad": "1",
                            "precio_unitario": "1000"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 404

    # Listado con filtro por estado
    await _crear_cotizacion(client, auth_headers, cli, prod)
    resp = await client.get("/api/v1/ventas/cotizaciones?estado=Borrador", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_editar_cotizacion_borrador_recalcula_totales(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)  # 5 uds, 10% desc

    # Editar: subir a 10 unidades, sin descuento, y cambiar el vendedor.
    resp = await client.put(
        f"/api/v1/ventas/cotizaciones/{cot['id']}",
        json={"fecha": date.today().isoformat(), "vigencia_dias": 30,
              "cliente_id": cli["id"], "vendedor": "Editado",
              "detalles": [{"producto_id": prod["id"], "cantidad": "10",
                            "precio_unitario": "20000.00", "descuento_porcentaje": "0"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    editada = resp.json()
    assert editada["numero"] == cot["numero"]         # el número se conserva
    assert editada["estado"] == "Borrador"
    assert editada["vendedor"] == "Editado"
    # 10 × 20.000 = 200.000; sin desc; IVA 19% = 38.000; total 238.000
    assert float(editada["subtotal"]) == 200000.0
    assert float(editada["descuento_total"]) == 0.0
    assert float(editada["iva_total"]) == 38000.0
    assert float(editada["total"]) == 238000.0
    assert len(editada["detalles"]) == 1
    assert float(editada["detalles"][0]["cantidad"]) == 10.0
    # Vigencia recalculada a 30 días
    assert editada["fecha_vencimiento"] == (date.today() + timedelta(days=30)).isoformat()


@pytest.mark.asyncio
async def test_editar_cotizacion_no_borrador_da_409(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)
    # Enviar → ya no es Borrador
    await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/enviar", headers=auth_headers)

    resp = await client.put(
        f"/api/v1/ventas/cotizaciones/{cot['id']}",
        json={"fecha": date.today().isoformat(), "vigencia_dias": 15,
              "cliente_id": cli["id"],
              "detalles": [{"producto_id": prod["id"], "cantidad": "1",
                            "precio_unitario": "20000.00", "descuento_porcentaje": "0"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_editar_cotizacion_inexistente_da_404(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    resp = await client.put(
        "/api/v1/ventas/cotizaciones/999999",
        json={"fecha": date.today().isoformat(), "vigencia_dias": 15,
              "cliente_id": cli["id"],
              "detalles": [{"producto_id": prod["id"], "cantidad": "1",
                            "precio_unitario": "20000.00", "descuento_porcentaje": "0"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_eliminar_cotizacion_borrador_deja_auditoria(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)

    resp = await client.delete(f"/api/v1/ventas/cotizaciones/{cot['id']}", headers=auth_headers)
    assert resp.status_code == 204, resp.text

    # Ya no existe
    resp = await client.get(f"/api/v1/ventas/cotizaciones/{cot['id']}", headers=auth_headers)
    assert resp.status_code == 404

    # Quedó registro de auditoría "Eliminar/Cotizacion"
    resp = await client.get(
        "/api/v1/auditoria", params={"entidad": "Cotizacion", "accion": "Eliminar"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    registros = resp.json()
    assert any(r["entidad_id"] == cot["id"] for r in registros)


@pytest.mark.asyncio
async def test_eliminar_cotizacion_no_borrador_da_409(client: AsyncClient, auth_headers: dict):
    cli, prod = await _cliente_y_producto(client, auth_headers)
    cot = await _crear_cotizacion(client, auth_headers, cli, prod)
    await client.post(f"/api/v1/ventas/cotizaciones/{cot['id']}/enviar", headers=auth_headers)

    resp = await client.delete(f"/api/v1/ventas/cotizaciones/{cot['id']}", headers=auth_headers)
    assert resp.status_code == 409, resp.text
    # Sigue existiendo
    resp = await client.get(f"/api/v1/ventas/cotizaciones/{cot['id']}", headers=auth_headers)
    assert resp.status_code == 200
