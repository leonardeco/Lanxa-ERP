"""
Gestión de usuarios (solo Admin): CRUD, toggle de acceso,
reset de contraseña por Admin y cambio de contraseña propia.
"""
import pytest
from httpx import AsyncClient


NUEVO_USUARIO = {
    "email": "aux1@test.com",
    "nombre_completo": "Auxiliar Uno",
    "rol": "Auxiliar",
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
    resp = await client.put("/api/v1/usuarios/99999", json={"rol": "Admin"}, headers=auth_headers)
    assert resp.status_code == 404

    # Rol inválido
    resp = await client.put(
        f"/api/v1/usuarios/{user['id']}", json={"rol": "Gerente"}, headers=auth_headers
    )
    assert resp.status_code == 400

    # Actualización válida de nombre y rol
    resp = await client.put(
        f"/api/v1/usuarios/{user['id']}",
        json={"nombre_completo": "Auxiliar Renombrado", "rol": "Administradora"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nombre_completo"] == "Auxiliar Renombrado"
    assert body["rol"] == "Administradora"


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

    # Contraseña demasiado corta
    resp = await client.put(
        f"/api/v1/usuarios/{user['id']}/reset-password",
        json={"new_password": "corta"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

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

    # Nueva contraseña demasiado corta
    resp = await client.put(
        "/api/v1/usuarios/me/password",
        json={"current_password": "testpassword", "new_password": "corta"},
        headers=auth_headers,
    )
    assert resp.status_code == 400

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
