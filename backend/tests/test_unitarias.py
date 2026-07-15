"""
Pruebas unitarias — Super Ozono Global ERP
Cubre: ventas CRUD, clientes, productos, usuarios, cálculo de totales y permisos.
"""

import pytest
from decimal import Decimal
from datetime import date
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

async def _crear_producto(client: AsyncClient, auth_headers: dict, sku: str = "TEST-001") -> dict:
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={
            "sku": sku,
            "nombre": "Producto Test",
            "marca": "Superozono",
            "precio_venta": "50000.00",
            "tarifa_iva": "19.00",
            "stock_actual": 100,
            "stock_minimo": 5,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_cliente(client: AsyncClient, auth_headers: dict, nit: str = "900123456-1") -> dict:
    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={
            "nit_cc": nit,
            "razon_social": "Cliente Test S.A.S.",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_venta(client: AsyncClient, auth_headers: dict, cliente_id: int, producto_id: int) -> dict:
    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": cliente_id,
            "detalles": [
                {
                    "producto_id": producto_id,
                    "cantidad": "2.00",
                    "precio_unitario": "50000.00",
                    "descuento_porcentaje": "0.00",
                    "iva_porcentaje": "19.00",
                }
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════
# PRODUCTOS
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_crear_producto_exitoso(client: AsyncClient, auth_headers: dict):
    producto = await _crear_producto(client, auth_headers, "PROD-A01")
    assert producto["sku"] == "PROD-A01"
    assert producto["nombre"] == "Producto Test"
    assert producto["id"] is not None


@pytest.mark.asyncio
async def test_crear_producto_sku_duplicado_falla(client: AsyncClient, auth_headers: dict):
    await _crear_producto(client, auth_headers, "PROD-DUP")
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={
            "sku": "PROD-DUP",
            "nombre": "Otro producto",
            "marca": "Ecoozono",
            "precio_venta": "10000.00",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "PROD-DUP" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_obtener_producto_por_id(client: AsyncClient, auth_headers: dict):
    creado = await _crear_producto(client, auth_headers, "PROD-GET")
    resp = await client.get(f"/api/v1/ventas/productos/{creado['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["sku"] == "PROD-GET"


@pytest.mark.asyncio
async def test_obtener_producto_inexistente_da_404(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/productos/999999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_listar_productos_retorna_lista(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/productos", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_actualizar_producto(client: AsyncClient, auth_headers: dict):
    creado = await _crear_producto(client, auth_headers, "PROD-UPD")
    resp = await client.put(
        f"/api/v1/ventas/productos/{creado['id']}",
        json={"nombre": "Producto Actualizado", "precio_venta": "75000.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Producto Actualizado"


@pytest.mark.asyncio
async def test_desactivar_producto_soft_delete(client: AsyncClient, auth_headers: dict):
    creado = await _crear_producto(client, auth_headers, "PROD-DEL")
    resp = await client.delete(f"/api/v1/ventas/productos/{creado['id']}", headers=auth_headers)
    assert resp.status_code == 200
    verify = await client.get(f"/api/v1/ventas/productos/{creado['id']}", headers=auth_headers)
    assert verify.json()["activo"] is False


# ══════════════════════════════════════════════════════════
# CLIENTES
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_crear_cliente_exitoso(client: AsyncClient, auth_headers: dict):
    cliente = await _crear_cliente(client, auth_headers, "800000001-1")
    assert cliente["nit_cc"] == "800000001-1"
    assert cliente["razon_social"] == "Cliente Test S.A.S."


@pytest.mark.asyncio
async def test_crear_cliente_nit_duplicado_falla(client: AsyncClient, auth_headers: dict):
    await _crear_cliente(client, auth_headers, "800000002-2")
    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "800000002-2", "razon_social": "Duplicado S.A."},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "800000002-2" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_listar_clientes_retorna_lista(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/clientes", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_cliente_inexistente_da_404(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/clientes/999999", headers=auth_headers)
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════
# VENTAS — CÁLCULO DE TOTALES
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_crear_venta_calcula_totales_correctamente(client: AsyncClient, auth_headers: dict):
    """
    Línea: 2 unidades × $50.000 → subtotal $100.000
    Sin descuento → base_gravable $100.000
    IVA 19% → $19.000
    Cliente por defecto NO es agente retenedor → sin retenciones.
    Total = $100.000 + $19.000 = $119.000
    (Las retenciones dependen del perfil del cliente; ver test dedicado.)
    """
    cliente = await _crear_cliente(client, auth_headers, "900000001-1")
    producto = await _crear_producto(client, auth_headers, "VENTA-001")

    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    assert Decimal(str(venta["subtotal"])) == Decimal("100000.00")
    assert Decimal(str(venta["iva_total"])) == Decimal("19000.00")
    assert Decimal(str(venta["retefuente"])) == Decimal("0.00")
    assert Decimal(str(venta["reteiva"])) == Decimal("0.00")
    assert Decimal(str(venta["reteica"])) == Decimal("0.00")
    assert Decimal(str(venta["total"])) == Decimal("119000.00")
    assert venta["estado"] == "Borrador"
    assert venta["estado_pago"] == "Pendiente"


@pytest.mark.asyncio
async def test_crear_venta_con_descuento(client: AsyncClient, auth_headers: dict):
    """10% descuento sobre $100.000 → base $90.000, IVA 19% = $17.100"""
    cliente = await _crear_cliente(client, auth_headers, "900000002-2")
    producto = await _crear_producto(client, auth_headers, "VENTA-002")

    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": cliente["id"],
            "detalles": [
                {
                    "producto_id": producto["id"],
                    "cantidad": "2.00",
                    "precio_unitario": "50000.00",
                    "descuento_porcentaje": "10.00",
                    "iva_porcentaje": "19.00",
                }
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert Decimal(str(data["descuento_total"])) == Decimal("10000.00")
    assert Decimal(str(data["base_gravable"])) == Decimal("90000.00")
    assert Decimal(str(data["iva_total"])) == Decimal("17100.00")


@pytest.mark.asyncio
async def test_venta_sin_detalles_da_error(client: AsyncClient, auth_headers: dict):
    cliente = await _crear_cliente(client, auth_headers, "900000003-3")
    resp = await client.post(
        "/api/v1/ventas/",
        json={"fecha": str(date.today()), "cliente_id": cliente["id"], "detalles": []},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_venta_cliente_inexistente_da_404(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": 999999,
            "detalles": [
                {"producto_id": 1, "cantidad": "1.00", "precio_unitario": "1000.00",
                 "descuento_porcentaje": "0.00", "iva_porcentaje": "19.00"}
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_venta_producto_inexistente_da_404(client: AsyncClient, auth_headers: dict):
    cliente = await _crear_cliente(client, auth_headers, "900000004-4")
    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": cliente["id"],
            "detalles": [
                {"producto_id": 999999, "cantidad": "1.00", "precio_unitario": "1000.00",
                 "descuento_porcentaje": "0.00", "iva_porcentaje": "19.00"}
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════
# VENTAS — CONFIRMAR Y ANULAR
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_confirmar_venta_cambia_estado(client: AsyncClient, auth_headers: dict):
    cliente = await _crear_cliente(client, auth_headers, "900001001-1")
    producto = await _crear_producto(client, auth_headers, "CONF-001")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["estado"] == "Confirmada"


@pytest.mark.asyncio
async def test_confirmar_venta_ya_confirmada_da_error(client: AsyncClient, auth_headers: dict):
    cliente = await _crear_cliente(client, auth_headers, "900001002-2")
    producto = await _crear_producto(client, auth_headers, "CONF-002")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])
    await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)

    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_anular_venta_cambia_estado(client: AsyncClient, auth_headers: dict):
    cliente = await _crear_cliente(client, auth_headers, "900001003-3")
    producto = await _crear_producto(client, auth_headers, "ANUL-001")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["detail"].__contains__("anulada")


@pytest.mark.asyncio
async def test_anular_venta_ya_anulada_da_error(client: AsyncClient, auth_headers: dict):
    cliente = await _crear_cliente(client, auth_headers, "900001004-4")
    producto = await _crear_producto(client, auth_headers, "ANUL-002")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])
    await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)

    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_numeros_venta_son_secuenciales(client: AsyncClient, auth_headers: dict):
    cliente = await _crear_cliente(client, auth_headers, "900002001-1")
    producto = await _crear_producto(client, auth_headers, "SEQ-001")
    v1 = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])
    v2 = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])
    assert v1["numero"].startswith("SOG-V-")
    assert v2["numero"].startswith("SOG-V-")
    n1 = int(v1["numero"].split("-")[-1])
    n2 = int(v2["numero"].split("-")[-1])
    assert n2 == n1 + 1


# ══════════════════════════════════════════════════════════
# USUARIOS
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_crear_usuario_email_duplicado_falla(client: AsyncClient, auth_headers: dict):
    payload = {
        "email": "duplicado@test.com",
        "nombre_completo": "Usuario Duplicado",
        "rol": "Auxiliar Contable",
        "is_active": True,
        "password": "password123",
    }
    resp1 = await client.post("/api/v1/usuarios", json=payload, headers=auth_headers)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/usuarios", json=payload, headers=auth_headers)
    assert resp2.status_code == 400
    assert "correo" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cambiar_contrasena_propia_correctamente(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/usuarios/me/password",
        json={"current_password": "testpassword", "new_password": "nuevapassword123"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cambiar_contrasena_incorrecta_da_error(client: AsyncClient, auth_headers: dict):
    resp = await client.put(
        "/api/v1/usuarios/me/password",
        json={"current_password": "contraseña_erronea", "new_password": "nueva12345"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_no_puede_toggle_a_si_mismo(client: AsyncClient, auth_headers: dict):
    me = await client.get("/api/users/me", headers=auth_headers)
    my_id = me.json()["id"]

    resp = await client.patch(f"/api/v1/usuarios/{my_id}/toggle", headers=auth_headers)
    assert resp.status_code == 400
    assert "ti mismo" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_listar_usuarios_solo_admin(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/usuarios", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


# ══════════════════════════════════════════════════════════
# PERMISOS — Auth y Rol
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_acceso_sin_token_da_401(client: AsyncClient):
    endpoints = [
        "/api/users/me",
        "/api/v1/ventas/",
        "/api/v1/ventas/productos",
        "/api/v1/ventas/clientes",
        "/api/v1/compras/",
        "/api/v1/inventario/dashboard",
        "/api/v1/contabilidad/cartera/stats",
        "/api/v1/reportes/aging-cartera",
    ]
    for endpoint in endpoints:
        resp = await client.get(endpoint)
        assert resp.status_code == 401, f"{endpoint} debería dar 401, dio {resp.status_code}"


@pytest.mark.asyncio
async def test_auxiliar_no_puede_crear_producto(client: AsyncClient, auth_headers: dict):
    """Crear producto requiere Admin o Administradora."""
    cr = await client.post(
        "/api/v1/usuarios",
        json={
            "email": "auxiliar.prod@test.com",
            "nombre_completo": "Auxiliar Test",
            "rol": "Auxiliar Contable",
            "is_active": True,
            "password": "password123",
        },
        headers=auth_headers,
    )
    assert cr.status_code == 201

    login = await client.post(
        "/api/login/access-token",
        data={"username": "auxiliar.prod@test.com", "password": "password123"},
    )
    aux_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "AUX-001", "nombre": "Producto Aux", "marca": "Test", "precio_venta": "1000.00"},
        headers=aux_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_auxiliar_no_puede_listar_usuarios(client: AsyncClient, auth_headers: dict):
    """Listar usuarios es solo para Admin."""
    await client.post(
        "/api/v1/usuarios",
        json={
            "email": "auxiliar.usr@test.com",
            "nombre_completo": "Auxiliar Usr",
            "rol": "Auxiliar Contable",
            "is_active": True,
            "password": "password123",
        },
        headers=auth_headers,
    )
    login = await client.post(
        "/api/login/access-token",
        data={"username": "auxiliar.usr@test.com", "password": "password123"},
    )
    aux_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/api/v1/usuarios", headers=aux_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_token_invalido_da_401(client: AsyncClient):
    resp = await client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer token_completamente_invalido"},
    )
    assert resp.status_code == 401


# ══════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_dashboard_ventas_estructura(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/ventas/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    required_keys = [
        "ventas_mes_actual", "ventas_mes_anterior", "cantidad_ventas_mes",
        "total_clientes_activos", "total_productos_activos", "ticket_promedio",
        "productos_stock_bajo", "ventas_por_marca",
    ]
    for key in required_keys:
        assert key in data, f"Falta campo '{key}' en dashboard de ventas"


@pytest.mark.asyncio
async def test_dashboard_inventario_estructura(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/inventario/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "valor_total_inventario" in data
    assert "productos_stock_bajo" in data
    assert "movimientos_mes" in data


def test_bogota_now_es_hora_local_utc_menos_5():
    """Las fechas de negocio (comprobantes, kardex) van en hora Colombia, no UTC."""
    from app.core.time import bogota_now, utcnow

    delta_horas = (utcnow() - bogota_now()).total_seconds() / 3600
    # Colombia es UTC-5 fijo (sin horario de verano)
    assert 4.9 < delta_horas < 5.1


def test_logging_persistente_escribe_archivo_rotado(tmp_path, monkeypatch):
    """14b: los eventos de structlog y logging estándar quedan en el archivo rotado."""
    import logging
    import structlog
    from app.core import logging_config

    monkeypatch.setattr(logging_config, "LOG_DIR", tmp_path)
    logging_config.configurar_logging(debug=False)

    structlog.get_logger("erp").info("evento_de_prueba", venta="SOG-V-0001")
    logging.getLogger("uvicorn.error").error("error de prueba stdlib")
    for h in logging.getLogger().handlers:
        h.flush()

    contenido = (tmp_path / "erp.log").read_text(encoding="utf-8")
    assert "evento_de_prueba" in contenido
    assert "error de prueba stdlib" in contenido
