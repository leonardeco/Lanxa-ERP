"""
Estados financieros construidos sobre el motor de asientos:
Estado de Resultados (P&L) y Balance General.
"""
import pytest
from httpx import AsyncClient


async def _venta_confirmada(client, headers, *, precio="100000.00", cantidad="2"):
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900300400", "razon_social": "Cliente PL SAS"},
        headers=headers,
    )).json()
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "PL-001", "nombre": "Biocida", "marca": "Superozono",
              "precio_venta": precio, "stock_actual": 100},
        headers=headers,
    )).json()
    venta = (await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": "2026-07-01",
            "cliente_id": cli["id"],
            "detalles": [{"producto_id": prod["id"], "cantidad": cantidad, "precio_unitario": precio}],
        },
        headers=headers,
    )).json()
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=headers)
    assert resp.status_code == 200, resp.text
    return venta


@pytest.mark.asyncio
async def test_estado_resultados_refleja_ingresos(client: AsyncClient, auth_headers: dict):
    await _venta_confirmada(client, auth_headers)  # base 200000, IVA 38000

    resp = await client.get(
        "/api/v1/reportes/estado-resultados?fecha_desde=2026-07-01&fecha_hasta=2026-07-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    pl = resp.json()

    assert float(pl["ingresos"]["total"]) == 200000.0  # base gravable, sin IVA
    codigos = [c["codigo_puc"] for c in pl["ingresos"]["cuentas"]]
    assert "413595" in codigos
    # Sin costos/gastos registrados aún: utilidad = ingresos
    assert float(pl["utilidad_bruta"]) == 200000.0
    assert float(pl["utilidad_neta"]) == 200000.0


@pytest.mark.asyncio
async def test_estado_resultados_periodo_sin_movimientos(client: AsyncClient, auth_headers: dict):
    await _venta_confirmada(client, auth_headers)

    # Un período donde no hubo ventas
    resp = await client.get(
        "/api/v1/reportes/estado-resultados?fecha_desde=2026-01-01&fecha_hasta=2026-01-31",
        headers=auth_headers,
    )
    pl = resp.json()
    assert float(pl["ingresos"]["total"]) == 0.0
    assert float(pl["utilidad_neta"]) == 0.0


@pytest.mark.asyncio
async def test_balance_general_cuadra(client: AsyncClient, auth_headers: dict):
    await _venta_confirmada(client, auth_headers)  # total 238000 a Clientes, IVA 38000 al pasivo

    resp = await client.get(
        "/api/v1/reportes/balance-general?fecha_corte=2026-07-31", headers=auth_headers
    )
    assert resp.status_code == 200
    bg = resp.json()

    # Activo: Clientes 238000 | Pasivo: IVA generado 38000 | Resultado: 200000
    assert float(bg["total_activo"]) == 238000.0
    assert float(bg["pasivo"]["total"]) == 38000.0
    assert float(bg["resultado_del_ejercicio"]) == 200000.0
    assert float(bg["total_pasivo_patrimonio"]) == 238000.0
    assert bg["cuadrado"] is True


@pytest.mark.asyncio
async def test_balance_sigue_cuadrado_tras_abono_y_compra(client: AsyncClient, auth_headers: dict):
    venta = await _venta_confirmada(client, auth_headers)

    # Abono a la CxC: mueve Clientes → Caja (el balance no cambia de total)
    cxc = next(
        c for c in (await client.get("/api/v1/contabilidad/cartera/cxc", headers=auth_headers)).json()
        if c["numero_factura"] == venta["numero"]
    )
    await client.post(
        f"/api/v1/contabilidad/cartera/cxc/{cxc['id']}/abonar",
        json={"valor": "100000.00"},
        headers=auth_headers,
    )

    # Compra confirmada: Inventario + IVA descontable vs Proveedores
    prov = (await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "800300400", "razon_social": "Proveedor PL"},
        headers=auth_headers,
    )).json()
    compra = (await client.post(
        "/api/v1/compras/",
        json={
            "fecha": "2026-07-02",
            "proveedor_id": prov["id"],
            "detalles": [{"descripcion": "Insumo", "cantidad": "5", "precio_unitario": "20000.00"}],
        },
        headers=auth_headers,
    )).json()
    await client.post(f"/api/v1/compras/{compra['id']}/confirmar", headers=auth_headers)

    resp = await client.get(
        "/api/v1/reportes/balance-general?fecha_corte=2026-07-31", headers=auth_headers
    )
    bg = resp.json()
    assert bg["cuadrado"] is True, bg

    # Caja aparece en el activo tras el abono
    activos = {c["codigo_puc"]: float(c["saldo"]) for c in bg["activo"]["cuentas"]}
    assert activos.get("110505") == 100000.0        # Caja
    assert activos.get("130505") == 138000.0        # Clientes (238000 - 100000)
    assert activos.get("143501") == 100000.0        # Inventario de la compra
    # IVA descontable resta del pasivo de IVA (saldo crédito neto)
    pasivos = {c["codigo_puc"]: float(c["saldo"]) for c in bg["pasivo"]["cuentas"]}
    assert pasivos.get("220501") == 119000.0        # Proveedores (100000 + IVA 19000)


@pytest.mark.asyncio
async def test_venta_anulada_no_afecta_estados(client: AsyncClient, auth_headers: dict):
    venta = await _venta_confirmada(client, auth_headers)
    await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)

    resp = await client.get(
        "/api/v1/reportes/estado-resultados?fecha_desde=2026-07-01&fecha_hasta=2026-07-31",
        headers=auth_headers,
    )
    assert float(resp.json()["ingresos"]["total"]) == 0.0

    resp = await client.get(
        "/api/v1/reportes/balance-general?fecha_corte=2026-07-31", headers=auth_headers
    )
    bg = resp.json()
    assert float(bg["total_activo"]) == 0.0
    assert bg["cuadrado"] is True
