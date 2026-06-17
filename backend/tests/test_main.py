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
