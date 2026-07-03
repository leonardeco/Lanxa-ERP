"""
Maestros contables: PUC, centros de costo, períodos, parámetros
tributarios y de nómina, terceros y dashboard.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1/contabilidad"


@pytest.mark.asyncio
async def test_dashboard_contabilidad(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"{BASE}/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["empresa_nit"]
    # El conftest siembra 2 parámetros tributarios
    assert data["total_parametros_tributarios"] >= 2


@pytest.mark.asyncio
async def test_puc_crud_completo(client: AsyncClient, auth_headers: dict):
    cuenta = {
        "codigo_puc": "110505",
        "nombre": "Caja general",
        "clase": "Activo",
        "naturaleza": "Débito",
        "nivel": "Subcuenta",
    }
    resp = await client.post(f"{BASE}/puc", json=cuenta, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    cuenta_id = resp.json()["id"]

    # Duplicado
    resp = await client.post(f"{BASE}/puc", json=cuenta, headers=auth_headers)
    assert resp.status_code == 400

    # GET por código
    resp = await client.get(f"{BASE}/puc/110505", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Caja general"

    resp = await client.get(f"{BASE}/puc/999999", headers=auth_headers)
    assert resp.status_code == 404

    # UPDATE
    resp = await client.put(
        f"{BASE}/puc/{cuenta_id}", json={"nombre": "Caja principal"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Caja principal"

    resp = await client.put(f"{BASE}/puc/99999", json={"nombre": "X"}, headers=auth_headers)
    assert resp.status_code == 404

    # TOGGLE
    resp = await client.patch(f"{BASE}/puc/{cuenta_id}/toggle", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["activo"] is False

    resp = await client.patch(f"{BASE}/puc/99999/toggle", headers=auth_headers)
    assert resp.status_code == 404

    # LIST
    resp = await client.get(f"{BASE}/puc", headers=auth_headers)
    assert any(c["codigo_puc"] == "110505" for c in resp.json())


@pytest.mark.asyncio
async def test_centros_costo_crud(client: AsyncClient, auth_headers: dict):
    cc = {"codigo": "CC-SUPER", "nombre": "Marca Superozono", "tipo": "Marca"}
    resp = await client.post(f"{BASE}/centros-costo", json=cc, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    cc_id = resp.json()["id"]

    resp = await client.post(f"{BASE}/centros-costo", json=cc, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.put(
        f"{BASE}/centros-costo/{cc_id}", json={"responsable": "Leo"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["responsable"] == "Leo"

    resp = await client.put(f"{BASE}/centros-costo/99999", json={"nombre": "X"}, headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.patch(f"{BASE}/centros-costo/{cc_id}/toggle", headers=auth_headers)
    assert resp.json()["activo"] is False
    resp = await client.patch(f"{BASE}/centros-costo/99999/toggle", headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.get(f"{BASE}/centros-costo", headers=auth_headers)
    assert any(c["codigo"] == "CC-SUPER" for c in resp.json())


@pytest.mark.asyncio
async def test_periodos_crear_y_cerrar(client: AsyncClient, auth_headers: dict):
    resp = await client.post(f"{BASE}/periodos", json={"anio": 2026, "mes": 7}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    periodo = resp.json()
    assert periodo["periodo"] == "2026-07"
    assert periodo["estado"] == "Abierto"

    # Duplicado
    resp = await client.post(f"{BASE}/periodos", json={"anio": 2026, "mes": 7}, headers=auth_headers)
    assert resp.status_code == 400

    # Cerrar (toggle) — registra fecha_cierre
    resp = await client.patch(f"{BASE}/periodos/{periodo['id']}/toggle", headers=auth_headers)
    assert resp.json()["estado"] == "Cerrado"
    assert resp.json()["fecha_cierre"] is not None

    # Reabrir — limpia fecha_cierre
    resp = await client.patch(f"{BASE}/periodos/{periodo['id']}/toggle", headers=auth_headers)
    assert resp.json()["estado"] == "Abierto"
    assert resp.json()["fecha_cierre"] is None

    resp = await client.patch(f"{BASE}/periodos/99999/toggle", headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.get(f"{BASE}/periodos", headers=auth_headers)
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_parametros_tributarios_update_y_toggle(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"{BASE}/parametros-tributarios", headers=auth_headers)
    assert resp.status_code == 200
    param = resp.json()[0]

    resp = await client.put(
        f"{BASE}/parametros-tributarios/{param['id']}",
        json={"notas": "Actualizado por test"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["notas"] == "Actualizado por test"

    resp = await client.put(
        f"{BASE}/parametros-tributarios/99999", json={"notas": "x"}, headers=auth_headers
    )
    assert resp.status_code == 404

    resp = await client.patch(
        f"{BASE}/parametros-tributarios/{param['id']}/toggle", headers=auth_headers
    )
    assert resp.json()["activo"] is False

    # El filtro activo=true ya no lo incluye
    resp = await client.get(f"{BASE}/parametros-tributarios?activo=true", headers=auth_headers)
    assert all(p["id"] != param["id"] for p in resp.json())

    resp = await client.patch(f"{BASE}/parametros-tributarios/99999/toggle", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_parametros_nomina_update_y_toggle(client: AsyncClient, auth_headers: dict):
    # No hay seed de nómina en tests: los 404 cubren el camino de error
    resp = await client.get(f"{BASE}/parametros-nomina", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.put(f"{BASE}/parametros-nomina/99999", json={"notas": "x"}, headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.patch(f"{BASE}/parametros-nomina/99999/toggle", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_terceros_lista_vacia(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"{BASE}/terceros", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
