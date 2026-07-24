"""Run 6 — CRUD y resumen mensual de Ventas Diarias."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _crear_producto(client: AsyncClient, auth_headers: dict, sku: str) -> int:
    r = await client.post(
        "/api/v1/ventas/productos",
        headers=auth_headers,
        json={
            "sku": sku,
            "nombre": f"Producto {sku}",
            "marca": "Test",
            "precio_venta": "100",
            "stock_actual": 10,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _crear_cliente(client: AsyncClient, auth_headers: dict, nit_cc: str) -> int:
    r = await client.post(
        "/api/v1/ventas/clientes",
        headers=auth_headers,
        json={
            "nit_cc": nit_cc,
            "razon_social": f"Cliente {nit_cc}",
            "tipo_persona": "Natural",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_crear_venta_diaria_calcula_saldo(client: AsyncClient, auth_headers: dict):
    producto_id = await _crear_producto(client, auth_headers, "PE-BIOCIDA")
    cliente_id = await _crear_cliente(client, auth_headers, "45095067")

    r = await client.post(
        "/api/v1/ventas-diarias/",
        headers=auth_headers,
        json={
            "fecha": "2026-01-28",
            "asesor": "MIGUEL B",
            "guia": "70223232",
            "codigo_guia": "KWHT",
            "cliente_id": cliente_id,
            "estado": "Entregado",
            "forma_pago": "Contraentrega",
            "detalles": [
                {"producto_id": producto_id, "cantidad": 2, "venta": 238, "abono_1": 30},
            ],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert float(body["detalles"][0]["saldo"]) == 208.0


@pytest.mark.asyncio
async def test_listar_ventas_diarias_filtra_por_estado(client: AsyncClient, auth_headers: dict):
    producto_id = await _crear_producto(client, auth_headers, "PE-STAR")
    cliente_id = await _crear_cliente(client, auth_headers, "76307082")

    await client.post(
        "/api/v1/ventas-diarias/",
        headers=auth_headers,
        json={
            "fecha": "2026-01-03",
            "cliente_id": cliente_id,
            "estado": "Devolución",
            "detalles": [{"producto_id": producto_id, "cantidad": 1, "venta": 100}],
        },
    )

    r = await client.get(
        "/api/v1/ventas-diarias/", headers=auth_headers, params={"estado": "Devolución"})
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    assert r.json()[0]["estado"] == "Devolución"


@pytest.mark.asyncio
async def test_resumen_mensual_suma_ventas_y_saldos(client: AsyncClient, auth_headers: dict):
    producto_id = await _crear_producto(client, auth_headers, "PE-SUELO")
    cliente_id = await _crear_cliente(client, auth_headers, "19226409")

    await client.post(
        "/api/v1/ventas-diarias/",
        headers=auth_headers,
        json={
            "fecha": "2026-02-10",
            "cliente_id": cliente_id,
            "estado": "Entregado",
            "detalles": [
                {"producto_id": producto_id, "cantidad": 1, "venta": 200, "abono_1": 50},
            ],
        },
    )

    r = await client.get("/api/v1/ventas-diarias/resumen/2026/2", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["total_venta"]) >= 200.0
    assert float(body["total_saldo"]) >= 150.0
    assert body["cantidad_entregado"] >= 1


@pytest.mark.asyncio
async def test_get_venta_diaria_inexistente_404(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/v1/ventas-diarias/999999", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_crear_venta_diaria_estado_invalido_da_422(client: AsyncClient, auth_headers: dict):
    """Un estado fuera de EstadoVentaDiaria debe rechazarse limpio (422),
    no reventar en un 500 al construir el ORM con EstadoVentaDiaria(...)."""
    producto_id = await _crear_producto(client, auth_headers, "PE-BADSTATE")
    cliente_id = await _crear_cliente(client, auth_headers, "11111111")

    r = await client.post(
        "/api/v1/ventas-diarias/",
        headers=auth_headers,
        json={
            "fecha": "2026-01-05",
            "cliente_id": cliente_id,
            "estado": "Enviado",  # no es un valor valido de EstadoVentaDiaria
            "detalles": [{"producto_id": producto_id, "cantidad": 1, "venta": 100}],
        },
    )
    assert r.status_code == 422
