"""
Gestión de usuarios (solo Admin): CRUD, toggle de acceso,
reset de contraseña por Admin y cambio de contraseña propia.
"""
import pytest
from httpx import AsyncClient

from app.core.security import get_password_hash
from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    apply_rls_tenant,
    reset_tenant_id,
    set_tenant_id,
)
from app.modules.usuarios.models import Usuario


NUEVO_USUARIO = {
    "email": "aux1@test.com",
    "nombre_completo": "Auxiliar Uno",
    "rol": "Auxiliar Contable",
    "is_active": True,
    "password": "password123",
}


async def _crear_usuario(client, headers, **overrides):
    resp = await client.post("/api/v1/usuarios", json={**NUEVO_USUARIO, **overrides}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_crear_usuario_rol_invalido_da_400(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/usuarios",
        json={**NUEVO_USUARIO, "rol": "Superjefe"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Rol inválido" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_crear_usuario_email_duplicado_da_400(client: AsyncClient, auth_headers: dict):
    await _crear_usuario(client, auth_headers)
    resp = await client.post("/api/v1/usuarios", json=NUEVO_USUARIO, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_usuario(client: AsyncClient, auth_headers: dict):
    user = await _crear_usuario(client, auth_headers)

    # 404 si no existe
    resp = await client.put("/api/v1/usuarios/99999", json={"rol": "Superusuario"}, headers=auth_headers)
    assert resp.status_code == 404

    # Rol inválido
    resp = await client.put(
        f"/api/v1/usuarios/{user['id']}", json={"rol": "Gerente"}, headers=auth_headers
    )
    assert resp.status_code == 400

    # Actualización válida de nombre y rol
    resp = await client.put(
        f"/api/v1/usuarios/{user['id']}",
        json={"nombre_completo": "Auxiliar Renombrado", "rol": "Directora"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nombre_completo"] == "Auxiliar Renombrado"
    assert body["rol"] == "Directora"


@pytest.mark.asyncio
async def test_toggle_usuario(client: AsyncClient, auth_headers: dict):
    user = await _crear_usuario(client, auth_headers)

    resp = await client.patch("/api/v1/usuarios/99999/toggle", headers=auth_headers)
    assert resp.status_code == 404

    # Desactivar
    resp = await client.patch(f"/api/v1/usuarios/{user['id']}/toggle", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Un usuario inactivo no puede loguearse
    resp = await client.post(
        "/api/login/access-token",
        data={"username": NUEVO_USUARIO["email"], "password": NUEVO_USUARIO["password"]},
    )
    assert resp.status_code == 400

    # Reactivar
    resp = await client.patch(f"/api/v1/usuarios/{user['id']}/toggle", headers=auth_headers)
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_admin_no_puede_desactivarse_a_si_mismo(client: AsyncClient, auth_headers: dict):
    me = await client.get("/api/users/me", headers=auth_headers)
    my_id = me.json()["id"]

    resp = await client.patch(f"/api/v1/usuarios/{my_id}/toggle", headers=auth_headers)
    assert resp.status_code == 400
    assert "ti mismo" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_reset_password_por_admin(client: AsyncClient, auth_headers: dict):
    user = await _crear_usuario(client, auth_headers)

    resp = await client.put(
        "/api/v1/usuarios/99999/reset-password",
        json={"new_password": "otraclave123"},
        headers=auth_headers,
    )
    assert resp.status_code == 404

    # Contraseña demasiado corta (Pydantic 422 o API 400)
    resp = await client.put(
        f"/api/v1/usuarios/{user['id']}/reset-password",
        json={"new_password": "corta"},
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)

    # Reset válido: la nueva contraseña sirve para loguearse, la vieja no
    resp = await client.put(
        f"/api/v1/usuarios/{user['id']}/reset-password",
        json={"new_password": "claveNueva2026"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.post(
        "/api/login/access-token",
        data={"username": NUEVO_USUARIO["email"], "password": NUEVO_USUARIO["password"]},
    )
    assert resp.status_code == 400

    resp = await client.post(
        "/api/login/access-token",
        data={"username": NUEVO_USUARIO["email"], "password": "claveNueva2026"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cambio_de_contrasena_propia(client: AsyncClient, auth_headers: dict):
    # Contraseña actual incorrecta
    resp = await client.put(
        "/api/v1/usuarios/me/password",
        json={"current_password": "incorrecta", "new_password": "claveNueva2026"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Nueva contraseña demasiado corta (Pydantic 422 o API 400)
    resp = await client.put(
        "/api/v1/usuarios/me/password",
        json={"current_password": "testpassword", "new_password": "corta"},
        headers=auth_headers,
    )
    assert resp.status_code in (400, 422)

    # Cambio válido y re-login con la nueva
    resp = await client.put(
        "/api/v1/usuarios/me/password",
        json={"current_password": "testpassword", "new_password": "claveNueva2026"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "claveNueva2026"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_listar_usuarios_ordenados(client: AsyncClient, auth_headers: dict):
    await _crear_usuario(client, auth_headers, email="zeta@test.com", nombre_completo="Zeta")
    await _crear_usuario(client, auth_headers, email="ana@test.com", nombre_completo="Ana")

    resp = await client.get("/api/v1/usuarios", headers=auth_headers)
    assert resp.status_code == 200
    nombres = [u["nombre_completo"] for u in resp.json()]
    assert nombres == sorted(nombres)


# ══════════════════════════════════════════════════════════
# 14c — Revocación de sesiones por Admin
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_revocar_sesiones_mata_el_refresh_token(client: AsyncClient, auth_headers: dict):
    usuario = await _crear_usuario(client, auth_headers)

    # El usuario inicia sesión: obtiene refresh token (cookie)
    login = await client.post(
        "/api/login/access-token",
        data={"username": usuario["email"], "password": "password123"},
    )
    assert login.status_code == 200
    assert client.cookies.get("refresh_token")

    # El Admin revoca sus sesiones
    resp = await client.post(
        f"/api/v1/usuarios/{usuario['id']}/revocar-sesiones", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["sesiones_revocadas"] == 1

    # El refresh token del usuario ya no sirve: la sesión no puede renovarse
    refresh = await client.post("/api/login/refresh-token")
    assert refresh.status_code == 401

    # La acción queda auditada
    log = (await client.get(
        "/api/v1/auditoria?entidad=Usuario&accion=Revocar sesiones", headers=auth_headers
    )).json()
    assert len(log) == 1
    assert usuario["email"] in log[0]["descripcion"]


@pytest.mark.asyncio
async def test_revocar_sesiones_usuario_inexistente_404(client: AsyncClient, auth_headers: dict):
    resp = await client.post("/api/v1/usuarios/99999/revocar-sesiones", headers=auth_headers)
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════
# Aislamiento cross-tenant: un Superusuario de un tenant no debe poder
# gestionar usuarios de OTRO tenant conociendo/adivinando su id
# (encontrado 2026-07-24 durante la verificación E2E de Run 6).
# ══════════════════════════════════════════════════════════

async def _crear_usuario_otro_tenant(db_session) -> int:
    """Crea un usuario en el tenant 2 y devuelve su id. Restaura el
    contexto de tenant al default al terminar."""
    db_session.add(Tenant(id=2, codigo="otro-tenant", razon_social="Otro Tenant", activo=True))
    await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    otro = Usuario(
        email="admin@otrotenant.com",
        nombre_completo="Admin Otro Tenant",
        rol="Superusuario",
        hashed_password=get_password_hash("password123"),
        tenant_id=2,
        is_active=True,
    )
    db_session.add(otro)
    await db_session.commit()
    await db_session.refresh(otro)
    other_id = otro.id
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)
    return other_id


@pytest.mark.asyncio
async def test_update_usuario_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    other_id = await _crear_usuario_otro_tenant(db_session)
    resp = await client.put(
        f"/api/v1/usuarios/{other_id}", json={"rol": "Auxiliar Contable"}, headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_toggle_usuario_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    other_id = await _crear_usuario_otro_tenant(db_session)
    resp = await client.patch(f"/api/v1/usuarios/{other_id}/toggle", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reset_password_usuario_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    other_id = await _crear_usuario_otro_tenant(db_session)
    resp = await client.put(
        f"/api/v1/usuarios/{other_id}/reset-password",
        json={"new_password": "otraclave123"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_revocar_sesiones_usuario_otro_tenant_404(client: AsyncClient, auth_headers: dict, db_session):
    other_id = await _crear_usuario_otro_tenant(db_session)
    resp = await client.post(f"/api/v1/usuarios/{other_id}/revocar-sesiones", headers=auth_headers)
    assert resp.status_code == 404
