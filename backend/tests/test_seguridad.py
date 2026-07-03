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


# ══════════════════════════════════════════════════════════
# SEC-006 — CORS wildcard bloqueado en producción
# ══════════════════════════════════════════════════════════

def test_sec_cors_wildcard_rechazado_en_produccion():
    from pydantic import ValidationError
    from app.core.config import Settings

    base = {"DATABASE_URL": "sqlite+aiosqlite:///:memory:", "SECRET_KEY": "x" * 64}

    # Con DEBUG=false, '*' debe ser rechazado por el validador
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None, DEBUG=False, CORS_ORIGINS="*", **base)

    # En desarrollo (DEBUG=true) se tolera
    s = Settings(_env_file=None, DEBUG=True, CORS_ORIGINS="*", **base)
    assert s.CORS_ORIGINS == "*"

    # Orígenes explícitos siempre válidos
    s = Settings(_env_file=None, DEBUG=False, CORS_ORIGINS="https://192.168.1.10:5173", **base)
    assert "192.168.1.10" in s.CORS_ORIGINS


@pytest.mark.asyncio
async def test_sec_headers_de_seguridad_presentes(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "same-origin"
    assert "max-age=" in resp.headers["strict-transport-security"]


# ══════════════════════════════════════════════════════════
# Robustez de auth (pendientes #1-5 de la sesión 2026-07-01)
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sec_token_con_sub_no_numerico_da_401(client: AsyncClient):
    """Un JWT firmado pero con sub no numérico debe dar 401, nunca 500."""
    from app.core.security import create_access_token

    token = create_access_token("no-soy-un-id")
    resp = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sec_login_no_revela_usuario_inactivo(client: AsyncClient, auth_headers: dict):
    """El login de un usuario inactivo responde igual que credenciales malas."""
    await client.post(
        "/api/v1/usuarios",
        json={"email": "inactivo3@test.com", "nombre_completo": "Inactivo", "rol": "Auxiliar",
              "is_active": True, "password": "password123"},
        headers=auth_headers,
    )
    usuarios = await client.get("/api/v1/usuarios", headers=auth_headers)
    uid = next(u["id"] for u in usuarios.json() if u["email"] == "inactivo3@test.com")
    await client.patch(f"/api/v1/usuarios/{uid}/toggle", headers=auth_headers)

    # Credenciales correctas pero cuenta inactiva
    r_inactivo = await client.post(
        "/api/login/access-token",
        data={"username": "inactivo3@test.com", "password": "password123"},
    )
    # Cuenta inexistente
    r_inexistente = await client.post(
        "/api/login/access-token",
        data={"username": "fantasma@test.com", "password": "password123"},
    )
    assert r_inactivo.status_code == r_inexistente.status_code == 400
    assert r_inactivo.json()["detail"] == r_inexistente.json()["detail"]


@pytest.mark.asyncio
async def test_sec_login_limpia_refresh_tokens_expirados(client: AsyncClient, db_session):
    """Los refresh tokens vencidos se purgan en cada login (la tabla no crece)."""
    from datetime import timedelta
    from sqlalchemy import select, func
    from app.core.time import utcnow
    from app.modules.usuarios.models import RefreshToken, Usuario

    admin_id = await db_session.scalar(select(Usuario.id).where(Usuario.email == "admin@test.com"))
    db_session.add(RefreshToken(
        usuario_id=admin_id,
        token_hash="hash-vencido-de-prueba",
        expires_at=utcnow() - timedelta(days=1),
    ))
    await db_session.commit()

    resp = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"},
    )
    assert resp.status_code == 200

    vencidos = await db_session.scalar(
        select(func.count(RefreshToken.id)).where(RefreshToken.token_hash == "hash-vencido-de-prueba")
    )
    assert vencidos == 0


@pytest.mark.asyncio
async def test_sec_guard_ultimo_admin(client: AsyncClient, auth_headers: dict):
    """No se puede degradar ni desactivar al único Admin activo del sistema."""
    me = (await client.get("/api/users/me", headers=auth_headers)).json()

    # Degradar el rol del único admin → 400
    resp = await client.put(
        f"/api/v1/usuarios/{me['id']}", json={"rol": "Auxiliar"}, headers=auth_headers
    )
    assert resp.status_code == 400
    assert "último Admin" in resp.json()["detail"]

    # Con un segundo Admin activo, sí se permite
    await client.post(
        "/api/v1/usuarios",
        json={"email": "admin2@test.com", "nombre_completo": "Admin Dos", "rol": "Admin",
              "is_active": True, "password": "password123"},
        headers=auth_headers,
    )
    resp = await client.put(
        f"/api/v1/usuarios/{me['id']}", json={"rol": "Administradora"}, headers=auth_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sec_listados_paginados(client: AsyncClient, auth_headers: dict):
    """limit/offset funcionan en los listados grandes."""
    for i in range(3):
        await client.post(
            "/api/v1/ventas/productos",
            json={"sku": f"PAG-{i}", "nombre": f"Prod {i}", "marca": "M", "precio_venta": "1"},
            headers=auth_headers,
        )
    resp = await client.get("/api/v1/ventas/productos?limit=2", headers=auth_headers)
    assert len(resp.json()) == 2
    resp = await client.get("/api/v1/ventas/productos?limit=2&offset=2", headers=auth_headers)
    assert len(resp.json()) == 1


def test_sec_hashes_de_passlib_siguen_verificando():
    """Migración passlib→bcrypt: los hashes existentes en BD deben seguir válidos.

    Hash generado con passlib 1.7.4 + bcrypt 4.0.1 el 2026-07-03 para la
    contraseña 'testpassword' — si esto falla, TODOS los usuarios reales
    quedarían bloqueados al desplegar."""
    from app.core.security import get_password_hash, verify_password

    hash_passlib = "$2b$12$3sIyHeJfAHzjPGs8Op28Ye92aLpNcnH5RS7agLwX06J4sDKwMWfLu"
    assert verify_password("testpassword", hash_passlib) is True
    assert verify_password("otra-clave", hash_passlib) is False

    # Los hashes nuevos también son $2b$ estándar y verifican
    nuevo = get_password_hash("ClaveNueva2026!")
    assert nuevo.startswith("$2b$12$")
    assert verify_password("ClaveNueva2026!", nuevo) is True

    # Contraseñas > 72 bytes: mismo comportamiento de truncado que passlib
    larga = "x" * 100
    h = get_password_hash(larga)
    assert verify_password(larga, h) is True
    assert verify_password("x" * 72, h) is True  # truncada al límite de bcrypt

    # Hash corrupto en BD → False, nunca excepción
    assert verify_password("lo-que-sea", "no-es-un-hash") is False
