import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash
from app.modules.usuarios.models import Usuario

@pytest.mark.asyncio
async def test_read_main(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code in [200, 404] # Si no existe health, 404 está bien, si existe 200

@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    response = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient, auth_headers):
    response = await client.get("/api/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["rol"] == "Admin"

@pytest.mark.asyncio
async def test_read_dashboard_inventario(client: AsyncClient, auth_headers):
    response = await client.get("/api/v1/inventario/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "valor_total_inventario" in data
    assert "productos_stock_bajo" in data

@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    login_resp = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"}
    )
    assert login_resp.status_code == 200
    old_refresh_cookie = client.cookies.get("refresh_token")
    assert old_refresh_cookie

    refresh_resp = await client.post("/api/login/refresh-token")
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

    new_refresh_cookie = client.cookies.get("refresh_token")
    assert new_refresh_cookie != old_refresh_cookie

    # El refresh token viejo ya fue rotado: reusarlo debe fallar
    reuse_resp = await client.post(
        "/api/login/refresh-token",
        cookies={"refresh_token": old_refresh_cookie},
    )
    assert reuse_resp.status_code == 401

@pytest.mark.asyncio
async def test_logout_revoca_refresh_token(client: AsyncClient):
    await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"}
    )
    refresh_cookie = client.cookies.get("refresh_token")
    assert refresh_cookie

    logout_resp = await client.post("/api/login/logout")
    assert logout_resp.status_code == 200

    reuse_resp = await client.post(
        "/api/login/refresh-token",
        cookies={"refresh_token": refresh_cookie},
    )
    assert reuse_resp.status_code == 401

@pytest.mark.asyncio
async def test_admin_resetea_password_de_otro_usuario(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/usuarios",
        json={
            "email": "auxiliar@test.com",
            "nombre_completo": "Auxiliar Test",
            "rol": "Auxiliar",
            "is_active": True,
            "password": "passwordvieja",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    reset_resp = await client.put(
        f"/api/v1/usuarios/{user_id}/reset-password",
        json={"new_password": "passwordnueva"},
        headers=auth_headers,
    )
    assert reset_resp.status_code == 200

    # La contraseña vieja ya no funciona, la nueva si
    old_login = await client.post(
        "/api/login/access-token",
        data={"username": "auxiliar@test.com", "password": "passwordvieja"},
    )
    assert old_login.status_code == 400

    new_login = await client.post(
        "/api/login/access-token",
        data={"username": "auxiliar@test.com", "password": "passwordnueva"},
    )
    assert new_login.status_code == 200

@pytest.mark.asyncio
async def test_no_admin_no_puede_resetear_password(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/usuarios",
        json={
            "email": "auxiliar2@test.com",
            "nombre_completo": "Auxiliar Test 2",
            "rol": "Auxiliar",
            "is_active": True,
            "password": "passwordvieja",
        },
        headers=auth_headers,
    )
    user_id = create_resp.json()["id"]

    login_resp = await client.post(
        "/api/login/access-token",
        data={"username": "auxiliar2@test.com", "password": "passwordvieja"},
    )
    auxiliar_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    reset_resp = await client.put(
        f"/api/v1/usuarios/{user_id}/reset-password",
        json={"new_password": "passwordnueva"},
        headers=auxiliar_headers,
    )
    assert reset_resp.status_code == 403

@pytest.mark.asyncio
async def test_rol_invalido_rechazado_por_constraint_de_bd(db_session):
    # Bypassea la validacion de la API: inserta directo con el ORM para
    # confirmar que la BD misma rechaza un rol que no sea uno de los validos.
    db_session.add(Usuario(
        email="hacker@test.com",
        nombre_completo="Rol Invalido",
        rol="Hacker",
        hashed_password=get_password_hash("password123"),
    ))
    with pytest.raises(IntegrityError):
        await db_session.commit()
