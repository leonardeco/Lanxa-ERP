"""
Pruebas de seguridad — Super Ozono Global ERP
Verifica autenticación, autorización, exposición de datos y comportamiento ante entradas maliciosas.
"""

import pytest
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════
# AUTENTICACIÓN — JWT
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sec_token_invalido_rechazado(client: AsyncClient):
    resp = await client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer ESTE_TOKEN_ES_BASURA"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sec_token_malformado_rechazado(client: AsyncClient):
    """Fragmento de JWT inválido (solo 2 partes en lugar de 3)."""
    resp = await client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.invalido"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sec_sin_header_de_auth_rechazado(client: AsyncClient):
    resp = await client.get("/api/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sec_esquema_bearer_obligatorio(client: AsyncClient, auth_headers: dict):
    """Basic auth o esquemas no estándar deben rechazarse."""
    token = auth_headers["Authorization"].split(" ")[1]
    resp = await client.get("/api/users/me", headers={"Authorization": f"Basic {token}"})
    assert resp.status_code == 401


# ══════════════════════════════════════════════════════════
# REFRESH TOKEN — seguridad de cookie
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sec_refresh_cookie_es_httponly(client: AsyncClient):
    """El refresh token debe tener httponly para proteger de XSS."""
    resp = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "refresh_token" in set_cookie, "No se encontró la cookie refresh_token"
    assert "httponly" in set_cookie.lower(), "La cookie refresh_token no tiene HttpOnly"


@pytest.mark.asyncio
async def test_sec_refresh_cookie_es_secure(client: AsyncClient):
    """El refresh token debe tener Secure para no transmitirse en HTTP plano."""
    resp = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "secure" in set_cookie.lower(), "La cookie refresh_token no tiene el flag Secure"


@pytest.mark.asyncio
async def test_sec_refresh_cookie_es_samesite_strict(client: AsyncClient):
    resp = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    set_cookie = resp.headers.get("set-cookie", "")
    assert "samesite=strict" in set_cookie.lower(), "La cookie no tiene SameSite=strict"


@pytest.mark.asyncio
async def test_sec_refresh_token_invalido_da_401(client: AsyncClient):
    client.cookies.set("refresh_token", "token_completamente_falso")
    resp = await client.post("/api/login/refresh-token")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sec_refresh_token_rotacion_invalida_viejo(client: AsyncClient):
    """Después de rotar el refresh token, el anterior debe ser inválido."""
    await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    old_refresh = client.cookies.get("refresh_token")
    assert old_refresh

    await client.post("/api/login/refresh-token")

    client.cookies.set("refresh_token", old_refresh)
    resp = await client.post("/api/login/refresh-token")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sec_logout_invalida_refresh_token(client: AsyncClient):
    """Después de logout, el refresh token debe ser inválido."""
    await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    refresh_cookie = client.cookies.get("refresh_token")
    assert refresh_cookie

    await client.post("/api/login/logout")

    client.cookies.set("refresh_token", refresh_cookie)
    resp = await client.post("/api/login/refresh-token")
    assert resp.status_code == 401


# ══════════════════════════════════════════════════════════
# AUTORIZACIÓN — Control de acceso por rol
# ══════════════════════════════════════════════════════════

async def _get_auxiliar_headers(client: AsyncClient, auth_headers: dict, suffix: str = "01") -> dict:
    """Crea un usuario Auxiliar y retorna sus auth headers."""
    await client.post(
        "/api/v1/usuarios",
        json={
            "email": f"auxiliar.sec{suffix}@test.com",
            "nombre_completo": f"Auxiliar Seguridad {suffix}",
            "rol": "Auxiliar",
            "is_active": True,
            "password": "password123",
        },
        headers=auth_headers,
    )
    login = await client.post(
        "/api/login/access-token",
        data={"username": f"auxiliar.sec{suffix}@test.com", "password": "password123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_sec_auxiliar_no_puede_crear_producto(client: AsyncClient, auth_headers: dict):
    aux_headers = await _get_auxiliar_headers(client, auth_headers, "02")
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "SEC-PROD", "nombre": "Test", "marca": "Test", "precio_venta": "1000.00"},
        headers=aux_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sec_auxiliar_no_puede_eliminar_cliente(client: AsyncClient, auth_headers: dict):
    cliente_resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "SEC-NIT-003", "razon_social": "Cliente Seguridad"},
        headers=auth_headers,
    )
    cliente_id = cliente_resp.json()["id"]
    aux_headers = await _get_auxiliar_headers(client, auth_headers, "03")
    resp = await client.delete(f"/api/v1/ventas/clientes/{cliente_id}", headers=aux_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sec_auxiliar_no_puede_listar_usuarios(client: AsyncClient, auth_headers: dict):
    aux_headers = await _get_auxiliar_headers(client, auth_headers, "04")
    resp = await client.get("/api/v1/usuarios", headers=aux_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sec_auxiliar_no_puede_anular_venta(client: AsyncClient, auth_headers: dict):
    """Anular ventas requiere Admin o Administradora."""
    # Crear venta como admin
    cliente_resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "SEC-NIT-005", "razon_social": "Cliente Anulación"},
        headers=auth_headers,
    )
    prod_resp = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "SEC-P05", "nombre": "Prod", "marca": "M", "precio_venta": "1000.00"},
        headers=auth_headers,
    )
    from datetime import date
    venta_resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": cliente_resp.json()["id"],
            "detalles": [{
                "producto_id": prod_resp.json()["id"],
                "cantidad": "1.00",
                "precio_unitario": "1000.00",
                "descuento_porcentaje": "0.00",
                "iva_porcentaje": "19.00",
            }],
        },
        headers=auth_headers,
    )
    venta_id = venta_resp.json()["id"]

    aux_headers = await _get_auxiliar_headers(client, auth_headers, "05")
    resp = await client.post(f"/api/v1/ventas/{venta_id}/anular", headers=aux_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sec_auxiliar_no_puede_resetear_password_ajena(client: AsyncClient, auth_headers: dict):
    target_resp = await client.post(
        "/api/v1/usuarios",
        json={
            "email": "victima.sec06@test.com",
            "nombre_completo": "Victima",
            "rol": "Auxiliar",
            "is_active": True,
            "password": "password123",
        },
        headers=auth_headers,
    )
    target_id = target_resp.json()["id"]

    aux_headers = await _get_auxiliar_headers(client, auth_headers, "06b")
    resp = await client.put(
        f"/api/v1/usuarios/{target_id}/reset-password",
        json={"new_password": "nueva12345"},
        headers=aux_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sec_contabilidad_dashboard_requiere_admin(client: AsyncClient, auth_headers: dict):
    aux_headers = await _get_auxiliar_headers(client, auth_headers, "07")
    resp = await client.get("/api/v1/contabilidad/dashboard", headers=aux_headers)
    assert resp.status_code == 403


# ══════════════════════════════════════════════════════════
# EXPOSICIÓN DE DATOS SENSIBLES
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sec_respuesta_no_expone_hashed_password(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/users/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "hashed_password" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_sec_lista_usuarios_no_expone_hashed_password(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/usuarios", headers=auth_headers)
    assert resp.status_code == 200
    for usuario in resp.json():
        assert "hashed_password" not in usuario
        assert "password" not in usuario


@pytest.mark.asyncio
async def test_sec_error_login_no_distingue_usuario_vs_password(client: AsyncClient):
    """Mismo mensaje de error para usuario inexistente y contraseña incorrecta (previene enumeración)."""
    resp_no_user = await client.post(
        "/api/login/access-token",
        data={"username": "noexiste@test.com", "password": "cualquier"},
    )
    resp_wrong_pass = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "incorrecta"},
    )
    assert resp_no_user.status_code == 400
    assert resp_wrong_pass.status_code == 400
    assert resp_no_user.json()["detail"] == resp_wrong_pass.json()["detail"]


# ══════════════════════════════════════════════════════════
# VALIDACIÓN DE INPUTS
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sec_contraseña_minimo_8_caracteres(client: AsyncClient, auth_headers: dict):
    """Contraseñas cortas deben ser rechazadas."""
    resp = await client.put(
        "/api/v1/usuarios/me/password",
        json={"current_password": "testpassword", "new_password": "corta"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sec_rol_invalido_rechazado(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/usuarios",
        json={
            "email": "hacker.sec@test.com",
            "nombre_completo": "Hacker",
            "rol": "Superadmin",
            "is_active": True,
            "password": "password123",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sec_inyeccion_sql_en_marca_no_causa_error(client: AsyncClient, auth_headers: dict):
    """Parámetros con metacaracteres SQL deben ser manejados sin errores 500."""
    resp = await client.get(
        "/api/v1/ventas/productos",
        params={"marca": "'; DROP TABLE productos; --"},
        headers=auth_headers,
    )
    assert resp.status_code < 500


@pytest.mark.asyncio
async def test_sec_inyeccion_sql_en_estado_no_causa_error(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        "/api/v1/ventas/",
        params={"estado": "' OR '1'='1"},
        headers=auth_headers,
    )
    assert resp.status_code < 500


@pytest.mark.asyncio
async def test_sec_payload_json_inesperado_no_causa_500(client: AsyncClient, auth_headers: dict):
    """JSON con campos extra no debería causar error de servidor."""
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={
            "sku": "SEC-EXTRA",
            "nombre": "Test",
            "marca": "M",
            "precio_venta": "1000.00",
            "campo_inesperado": "valor_malicioso",
            "__class__": "exploit",
        },
        headers=auth_headers,
    )
    assert resp.status_code in (201, 400, 422)
    assert resp.status_code < 500


# ══════════════════════════════════════════════════════════
# INTEGRIDAD DE SESIÓN
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sec_usuario_inactivo_no_puede_autenticarse(client: AsyncClient, auth_headers: dict):
    """Un usuario desactivado no debe poder loguearse."""
    await client.post(
        "/api/v1/usuarios",
        json={
            "email": "inactivo.sec@test.com",
            "nombre_completo": "Usuario Inactivo",
            "rol": "Auxiliar",
            "is_active": True,
            "password": "password123",
        },
        headers=auth_headers,
    )
    # Obtener ID del nuevo usuario
    usuarios = await client.get("/api/v1/usuarios", headers=auth_headers)
    user_id = next(u["id"] for u in usuarios.json() if u["email"] == "inactivo.sec@test.com")

    # Desactivar
    await client.patch(f"/api/v1/usuarios/{user_id}/toggle", headers=auth_headers)

    # Intentar login
    resp = await client.post(
        "/api/login/access-token",
        data={"username": "inactivo.sec@test.com", "password": "password123"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_sec_usuario_inactivo_con_token_valido_rechazado(client: AsyncClient, auth_headers: dict):
    """Si un usuario se desactiva, sus tokens existentes deben ser rechazados."""
    await client.post(
        "/api/v1/usuarios",
        json={
            "email": "inactivo2.sec@test.com",
            "nombre_completo": "Usuario Inactivo 2",
            "rol": "Auxiliar",
            "is_active": True,
            "password": "password123",
        },
        headers=auth_headers,
    )
    # Login como el nuevo usuario para obtener token
    login = await client.post(
        "/api/login/access-token",
        data={"username": "inactivo2.sec@test.com", "password": "password123"},
    )
    user_token = login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Obtener su ID y desactivarlo como admin
    usuarios = await client.get("/api/v1/usuarios", headers=auth_headers)
    user_id = next(u["id"] for u in usuarios.json() if u["email"] == "inactivo2.sec@test.com")
    await client.patch(f"/api/v1/usuarios/{user_id}/toggle", headers=auth_headers)

    # El token sigue siendo técnicamente válido (JWT no blacklisted),
    # pero get_current_user verifica is_active → debe dar 400
    resp = await client.get("/api/users/me", headers=user_headers)
    assert resp.status_code == 400
