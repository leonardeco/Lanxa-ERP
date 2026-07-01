"""
Pruebas de humo — Super Ozono Global ERP
Verifica que todos los endpoints principales respondan sin errores 5xx.
"""

import pytest
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════
# SISTEMA
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "application/json" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_smoke_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_smoke_docs_disponibles(client: AsyncClient):
    resp = await client.get("/docs")
    assert resp.status_code == 200


# ══════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_login_exitoso(client: AsyncClient):
    resp = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_smoke_login_credenciales_invalidas(client: AsyncClient):
    resp = await client.post(
        "/api/login/access-token",
        data={"username": "nadie@test.com", "password": "nada"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_smoke_users_me(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


# ══════════════════════════════════════════════════════════
# MÓDULO VENTAS
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_ventas_dashboard(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    assert "ventas_mes_actual" in resp.json()


@pytest.mark.asyncio
async def test_smoke_ventas_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_ventas_productos_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/productos", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_ventas_clientes_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/clientes", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ══════════════════════════════════════════════════════════
# MÓDULO COMPRAS
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_compras_dashboard(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/compras/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    assert "total_compras_mes" in resp.json()


@pytest.mark.asyncio
async def test_smoke_compras_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/compras/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_compras_proveedores_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/compras/proveedores", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ══════════════════════════════════════════════════════════
# MÓDULO INVENTARIO
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_inventario_dashboard(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/inventario/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "valor_total_inventario" in data
    assert "productos_stock_bajo" in data


@pytest.mark.asyncio
async def test_smoke_inventario_movimientos(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/inventario/movimientos", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ══════════════════════════════════════════════════════════
# MÓDULO CONTABILIDAD
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_contabilidad_dashboard(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_cuentas_puc" in data
    assert "empresa_nit" in data


@pytest.mark.asyncio
async def test_smoke_contabilidad_puc_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/puc", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_contabilidad_centros_costo(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/centros-costo", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_contabilidad_periodos(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/periodos", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_contabilidad_terceros(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/terceros", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_cartera_stats(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/cartera/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "cxc_pendiente" in data
    assert "cxp_pendiente" in data


@pytest.mark.asyncio
async def test_smoke_cartera_cxc_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/cartera/cxc", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_cartera_cxp_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/cartera/cxp", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_cartera_pagos_list(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/cartera/pagos", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_parametros_tributarios(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/parametros-tributarios", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_smoke_parametros_nomina(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/contabilidad/parametros-nomina", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ══════════════════════════════════════════════════════════
# MÓDULO REPORTES
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_reporte_aging_cartera(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/reportes/aging-cartera", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "cxc" in data
    assert "cxp" in data


@pytest.mark.asyncio
async def test_smoke_reporte_compras_periodo(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/reportes/compras-periodo", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "fecha_desde" in data


@pytest.mark.asyncio
async def test_smoke_reporte_ventas_periodo(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/reportes/ventas-periodo", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "por_cliente" in data


@pytest.mark.asyncio
async def test_smoke_reporte_retenciones_periodo(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/reportes/retenciones-periodo", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_retefuente" in data
    assert "total_reteiva" in data


# ══════════════════════════════════════════════════════════
# MÓDULO ALEGRA (no requiere credenciales reales — devuelve 400)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_alegra_status_sin_credenciales(client: AsyncClient, auth_headers: dict):
    """Sin ALEGRA_EMAIL/TOKEN configurados, el endpoint devuelve 400, no 500."""
    resp = await client.get("/api/v1/alegra/status", headers=auth_headers)
    assert resp.status_code in (200, 400)
    assert resp.status_code < 500


@pytest.mark.asyncio
async def test_smoke_alegra_facturas_sin_credenciales(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/alegra/facturas", headers=auth_headers)
    assert resp.status_code in (200, 400)
    assert resp.status_code < 500


# ══════════════════════════════════════════════════════════
# COBERTURA: todos los módulos requieren auth
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_smoke_todos_los_modulos_requieren_auth(client: AsyncClient):
    """Ningún endpoint de negocio debe ser accesible sin token."""
    endpoints_protegidos = [
        "/api/users/me",
        "/api/v1/ventas/",
        "/api/v1/ventas/productos",
        "/api/v1/ventas/clientes",
        "/api/v1/ventas/dashboard",
        "/api/v1/compras/",
        "/api/v1/compras/proveedores",
        "/api/v1/compras/dashboard",
        "/api/v1/inventario/dashboard",
        "/api/v1/inventario/movimientos",
        "/api/v1/contabilidad/dashboard",
        "/api/v1/contabilidad/puc",
        "/api/v1/contabilidad/cartera/stats",
        "/api/v1/reportes/aging-cartera",
        "/api/v1/alegra/status",
    ]
    for path in endpoints_protegidos:
        resp = await client.get(path)
        assert resp.status_code in (401, 403), (
            f"FALLO: GET {path} sin token devolvió {resp.status_code} (esperado 401/403)"
        )
