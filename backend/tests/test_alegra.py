"""
Integración Alegra (facturación electrónica) con el cliente HTTP mockeado:
status, taxes, sincronización de clientes/productos y envío de facturas.
"""
import pytest
from httpx import AsyncClient

from app.modules.alegra import router as alegra_router

BASE = "/api/v1/alegra"


@pytest.fixture
def alegra_credenciales(monkeypatch):
    """Simula credenciales configuradas en .env."""
    monkeypatch.setattr(alegra_router.settings, "ALEGRA_EMAIL", "erp@superozono.test")
    monkeypatch.setattr(alegra_router.settings, "ALEGRA_TOKEN", "token-de-prueba")


async def _crear_cliente(client, headers, **overrides):
    payload = {
        "nit_cc": "900777888",
        "razon_social": "Cliente Alegra S.A.S.",
        "email": "cliente@test.com",
        "telefono": "6067001122",
        "direccion": "Calle 1 # 2-3",
        "ciudad": "Armenia",
        **overrides,
    }
    resp = await client.post("/api/v1/ventas/clientes", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_producto(client, headers, **overrides):
    payload = {
        "sku": "ALG-001",
        "nombre": "Biocida 1L",
        "marca": "Superozono",
        "precio_venta": "50000.00",
        **overrides,
    }
    resp = await client.post("/api/v1/ventas/productos", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════
# Credenciales y status
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sin_credenciales_da_400(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"{BASE}/status", headers=auth_headers)
    assert resp.status_code == 400
    assert "ALEGRA_EMAIL" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_status_conectado(client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch):
    async def fake_get(path, params=None):
        assert path == "/company"
        return {"name": "Super Ozono", "identification": "901841798", "plan": {"name": "Pyme"}}

    monkeypatch.setattr(alegra_router, "alegra_get", fake_get)
    resp = await client.get(f"{BASE}/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["conectado"] is True
    assert data["empresa"] == "Super Ozono"
    assert data["plan"] == "Pyme"


@pytest.mark.asyncio
async def test_status_error_de_conexion(client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch):
    async def fake_get(path, params=None):
        raise RuntimeError("timeout simulado")

    monkeypatch.setattr(alegra_router, "alegra_get", fake_get)
    resp = await client.get(f"{BASE}/status", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["conectado"] is False
    assert "timeout" in resp.json()["error"]


@pytest.mark.asyncio
async def test_taxes_exito_y_error(client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch):
    async def fake_get(path, params=None):
        return [{"id": 3, "name": "IVA 19%"}]

    monkeypatch.setattr(alegra_router, "alegra_get", fake_get)
    resp = await client.get(f"{BASE}/taxes", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == 3

    async def fake_get_falla(path, params=None):
        raise RuntimeError("api caida")

    monkeypatch.setattr(alegra_router, "alegra_get", fake_get_falla)
    resp = await client.get(f"{BASE}/taxes", headers=auth_headers)
    assert resp.status_code == 502


# ══════════════════════════════════════════════════════════
# Sincronización de clientes y productos
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_sync_cliente_crea_y_actualiza(client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch):
    cliente = await _crear_cliente(client, auth_headers)
    llamadas = {"post": 0, "put": 0}

    async def fake_post(path, payload):
        llamadas["post"] += 1
        assert path == "/contacts"
        assert payload["identification"] == "900777888"
        assert payload["email"] == "cliente@test.com"
        return {"id": 501, "name": payload["name"]}

    async def fake_put(path, payload):
        llamadas["put"] += 1
        assert path == "/contacts/501"
        return {"id": 501, "name": payload["name"]}

    monkeypatch.setattr(alegra_router, "alegra_post", fake_post)
    monkeypatch.setattr(alegra_router, "alegra_put", fake_put)

    # Primera sync → POST (crear) y guarda alegra_id
    resp = await client.post(f"{BASE}/sync/cliente/{cliente['id']}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["alegra_id"] == 501

    # Segunda sync → PUT (actualizar), no vuelve a crear
    resp = await client.post(f"{BASE}/sync/cliente/{cliente['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert llamadas == {"post": 1, "put": 1}

    resp = await client.post(f"{BASE}/sync/cliente/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sync_cliente_persona_natural(client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch):
    cliente = await _crear_cliente(
        client, auth_headers, nit_cc="1094900000", tipo_persona="Natural", razon_social="Juan Pérez"
    )

    async def fake_post(path, payload):
        # Rama de persona natural en el mapper
        assert payload["nameObject"] == {"firstName": "Juan Pérez"}
        return {"id": 502, "name": payload["name"]}

    monkeypatch.setattr(alegra_router, "alegra_post", fake_post)
    resp = await client.post(f"{BASE}/sync/cliente/{cliente['id']}", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sync_cliente_error_de_api_da_502(
    client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch
):
    cliente = await _crear_cliente(client, auth_headers)

    async def fake_post(path, payload):
        raise RuntimeError("500 desde Alegra")

    monkeypatch.setattr(alegra_router, "alegra_post", fake_post)
    resp = await client.post(f"{BASE}/sync/cliente/{cliente['id']}", headers=auth_headers)
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_sync_producto_crea_y_actualiza(
    client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch
):
    producto = await _crear_producto(client, auth_headers)
    llamadas = {"post": 0, "put": 0}

    async def fake_post(path, payload):
        llamadas["post"] += 1
        assert path == "/items"
        assert payload["reference"] == "ALG-001"
        return {"id": 801, "name": payload["name"]}

    async def fake_put(path, payload):
        llamadas["put"] += 1
        assert path == "/items/801"
        return {"id": 801, "name": payload["name"]}

    monkeypatch.setattr(alegra_router, "alegra_post", fake_post)
    monkeypatch.setattr(alegra_router, "alegra_put", fake_put)

    resp = await client.post(f"{BASE}/sync/producto/{producto['id']}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["alegra_id"] == 801

    resp = await client.post(f"{BASE}/sync/producto/{producto['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert llamadas == {"post": 1, "put": 1}

    resp = await client.post(f"{BASE}/sync/producto/99999", headers=auth_headers)
    assert resp.status_code == 404


# ══════════════════════════════════════════════════════════
# Envío de facturas
# ══════════════════════════════════════════════════════════

async def _crear_venta(client, headers, cliente_id, producto_id):
    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": "2026-07-01",
            "cliente_id": cliente_id,
            "detalles": [{"producto_id": producto_id, "cantidad": "1", "precio_unitario": "50000.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_enviar_factura_flujo_completo(client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch):
    cliente = await _crear_cliente(client, auth_headers)
    producto = await _crear_producto(client, auth_headers)
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    # Sin sincronizar el cliente → 400
    resp = await client.post(f"{BASE}/facturas/{venta['id']}", headers=auth_headers)
    assert resp.status_code == 400
    assert "cliente" in resp.json()["detail"].lower()

    # Sincronizar cliente pero no el producto → 400
    async def fake_post_sync(path, payload):
        return {"id": 601, "name": payload["name"]}

    monkeypatch.setattr(alegra_router, "alegra_post", fake_post_sync)
    await client.post(f"{BASE}/sync/cliente/{cliente['id']}", headers=auth_headers)

    resp = await client.post(f"{BASE}/facturas/{venta['id']}", headers=auth_headers)
    assert resp.status_code == 400
    assert "producto" in resp.json()["detail"].lower()

    # Sincronizar el producto y enviar la factura
    await client.post(f"{BASE}/sync/producto/{producto['id']}", headers=auth_headers)

    async def fake_post_factura(path, payload):
        assert path == "/invoices"
        assert payload["client"] == {"id": 601}
        return {
            "id": 9001,
            "numberTemplate": {"fullNumber": "FE-123"},
            "stamp": {"cufe": "cufe-abc-123"},
        }

    monkeypatch.setattr(alegra_router, "alegra_post", fake_post_factura)
    resp = await client.post(f"{BASE}/facturas/{venta['id']}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["alegra_id"] == 9001
    assert data["numero_factura"] == "FE-123"
    assert data["cufe"] == "cufe-abc-123"
    assert data["estado"] == "Facturada"

    # La venta quedó FACTURADA y no se puede reenviar
    resp = await client.get(f"/api/v1/ventas/{venta['id']}", headers=auth_headers)
    assert resp.json()["estado"] == "Facturada"

    resp = await client.post(f"{BASE}/facturas/{venta['id']}", headers=auth_headers)
    assert resp.status_code == 400
    assert "ya fue enviada" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_enviar_factura_validaciones(client: AsyncClient, auth_headers: dict, alegra_credenciales):
    resp = await client.post(f"{BASE}/facturas/99999", headers=auth_headers)
    assert resp.status_code == 404

    # Venta anulada no se puede facturar
    cliente = await _crear_cliente(client, auth_headers)
    producto = await _crear_producto(client, auth_headers)
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])
    await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)

    resp = await client.post(f"{BASE}/facturas/{venta['id']}", headers=auth_headers)
    assert resp.status_code == 400
    assert "anulada" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_listar_facturas_de_alegra(client: AsyncClient, auth_headers: dict, alegra_credenciales, monkeypatch):
    async def fake_get(path, params=None):
        assert path == "/invoices"
        assert params == {"limit": 20, "start": 0}
        return [{"id": 1, "total": 119000}]

    monkeypatch.setattr(alegra_router, "alegra_get", fake_get)
    resp = await client.get(f"{BASE}/facturas", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == 1
