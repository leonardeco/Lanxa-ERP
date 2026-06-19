import pytest
from httpx import AsyncClient

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
