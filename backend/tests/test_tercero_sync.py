"""#14a — puente Cliente/Proveedor → Tercero al crear/editar maestros comerciales."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _terceros_por_nit(client: AsyncClient, headers: dict, nit: str) -> list[dict]:
    resp = await client.get("/api/v1/contabilidad/terceros", headers=headers)
    assert resp.status_code == 200, resp.text
    return [t for t in resp.json() if t["nit_cc"] == nit]


@pytest.mark.asyncio
async def test_crear_cliente_crea_tercero(client: AsyncClient, auth_headers: dict):
    nit = "900700100"
    resp = await client.post(
        "/api/v1/ventas/clientes",
        headers=auth_headers,
        json={"nit_cc": nit, "razon_social": "Cliente Puente SAS"},
    )
    assert resp.status_code == 201, resp.text

    terceros = await _terceros_por_nit(client, auth_headers, nit)
    assert len(terceros) == 1
    assert terceros[0]["razon_social"] == "Cliente Puente SAS"
    assert terceros[0]["tipo"] in ("Cliente", "Mixto")


@pytest.mark.asyncio
async def test_crear_proveedor_crea_tercero(client: AsyncClient, auth_headers: dict):
    nit = "800700200"
    resp = await client.post(
        "/api/v1/compras/proveedores",
        headers=auth_headers,
        json={"nit_cc": nit, "razon_social": "Proveedor Puente Ltda"},
    )
    assert resp.status_code == 201, resp.text

    terceros = await _terceros_por_nit(client, auth_headers, nit)
    assert len(terceros) == 1
    assert terceros[0]["razon_social"] == "Proveedor Puente Ltda"
    assert terceros[0]["tipo"] in ("Proveedor", "Mixto")


@pytest.mark.asyncio
async def test_mismo_nit_cliente_y_proveedor_queda_mixto(
    client: AsyncClient, auth_headers: dict
):
    nit = "901888777"
    r1 = await client.post(
        "/api/v1/ventas/clientes",
        headers=auth_headers,
        json={"nit_cc": nit, "razon_social": "Mixto SA"},
    )
    assert r1.status_code == 201, r1.text
    r2 = await client.post(
        "/api/v1/compras/proveedores",
        headers=auth_headers,
        json={"nit_cc": nit, "razon_social": "Mixto SA"},
    )
    assert r2.status_code == 201, r2.text

    terceros = await _terceros_por_nit(client, auth_headers, nit)
    assert len(terceros) == 1
    assert terceros[0]["tipo"] == "Mixto"


@pytest.mark.asyncio
async def test_actualizar_cliente_actualiza_razon_tercero(
    client: AsyncClient, auth_headers: dict
):
    nit = "900700300"
    create = await client.post(
        "/api/v1/ventas/clientes",
        headers=auth_headers,
        json={"nit_cc": nit, "razon_social": "Nombre Viejo"},
    )
    assert create.status_code == 201, create.text
    cid = create.json()["id"]

    upd = await client.put(
        f"/api/v1/ventas/clientes/{cid}",
        headers=auth_headers,
        json={"razon_social": "Nombre Nuevo SAS"},
    )
    assert upd.status_code == 200, upd.text

    terceros = await _terceros_por_nit(client, auth_headers, nit)
    assert len(terceros) == 1
    assert terceros[0]["razon_social"] == "Nombre Nuevo SAS"
