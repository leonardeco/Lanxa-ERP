"""
Auditoría de cambios (#19): quién modificó qué en datos maestros
(productos, clientes, proveedores, parámetros) y acciones administrativas
(usuarios, períodos). El registro viaja en la misma transacción del cambio.
"""
import pytest
from httpx import AsyncClient


async def _crear_producto(client, headers, sku="AUD-001"):
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": sku, "nombre": "Biocida Auditado", "marca": "Superozono",
              "precio_venta": "10000", "stock_actual": 10},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_ciclo_producto_queda_auditado(client: AsyncClient, auth_headers: dict):
    prod = await _crear_producto(client, auth_headers)

    # Actualizar precio y desactivar
    resp = await client.put(
        f"/api/v1/ventas/productos/{prod['id']}",
        json={"precio_venta": "12500"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    await client.delete(f"/api/v1/ventas/productos/{prod['id']}", headers=auth_headers)

    log = (await client.get(
        "/api/v1/auditoria?entidad=Producto", headers=auth_headers)).json()
    acciones = [(r["accion"], r["entidad_id"]) for r in log]
    assert ("Crear", prod["id"]) in acciones
    assert ("Actualizar", prod["id"]) in acciones
    assert ("Desactivar", prod["id"]) in acciones

    # El update guarda el diff campo a campo con antes/después
    upd = next(r for r in log if r["accion"] == "Actualizar")
    assert upd["usuario_email"] == "admin@test.com"
    assert upd["cambios"]["precio_venta"]["antes"] == "10000.00"
    assert upd["cambios"]["precio_venta"]["despues"] == "12500"
    assert "AUD-001" in upd["descripcion"]


@pytest.mark.asyncio
async def test_update_sin_cambios_reales_no_registra(client: AsyncClient, auth_headers: dict):
    prod = await _crear_producto(client, auth_headers, sku="AUD-002")

    # PUT con el mismo nombre que ya tiene → no hay diff → no se audita
    resp = await client.put(
        f"/api/v1/ventas/productos/{prod['id']}",
        json={"nombre": "Biocida Auditado"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    log = (await client.get(
        "/api/v1/auditoria?entidad=Producto&accion=Actualizar", headers=auth_headers)).json()
    assert log == []


@pytest.mark.asyncio
async def test_cliente_y_proveedor_auditados(client: AsyncClient, auth_headers: dict):
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900555777", "razon_social": "Cliente Auditado SAS"},
        headers=auth_headers,
    )).json()
    await client.put(
        f"/api/v1/ventas/clientes/{cli['id']}",
        json={"dias_credito": 60},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "800555777", "razon_social": "Proveedor Auditado"},
        headers=auth_headers,
    )

    log_cli = (await client.get(
        "/api/v1/auditoria?entidad=Cliente", headers=auth_headers)).json()
    assert [r["accion"] for r in log_cli] == ["Actualizar", "Crear"]  # desc por fecha
    assert log_cli[0]["cambios"]["dias_credito"] == {"antes": 30, "despues": 60}

    log_prov = (await client.get(
        "/api/v1/auditoria?entidad=Proveedor", headers=auth_headers)).json()
    assert len(log_prov) == 1 and log_prov[0]["accion"] == "Crear"


@pytest.mark.asyncio
async def test_parametro_tributario_auditado(client: AsyncClient, auth_headers: dict):
    params = (await client.get(
        "/api/v1/contabilidad/parametros-tributarios", headers=auth_headers)).json()
    reteiva = next(p for p in params if p["concepto"] == "ReteIVA")

    resp = await client.put(
        f"/api/v1/contabilidad/parametros-tributarios/{reteiva['id']}",
        json={"tarifa_valor": "0.10000"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    log = (await client.get(
        "/api/v1/auditoria?entidad=ParametroTributario", headers=auth_headers)).json()
    assert len(log) == 1
    assert log[0]["cambios"]["tarifa_valor"]["antes"] == "0.15000"
    assert "ReteIVA" in log[0]["descripcion"]


@pytest.mark.asyncio
async def test_acciones_de_usuarios_auditadas_sin_password(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/usuarios",
        json={"email": "auditado@test.com", "nombre_completo": "Usuario Auditado",
              "rol": "Auxiliar Contable", "is_active": True, "password": "secreta123"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    uid = resp.json()["id"]

    await client.put(
        f"/api/v1/usuarios/{uid}",
        json={"rol": "Directora"},
        headers=auth_headers,
    )
    await client.put(
        f"/api/v1/usuarios/{uid}/reset-password",
        json={"new_password": "otraclave123"},
        headers=auth_headers,
    )

    log = (await client.get(
        "/api/v1/auditoria?entidad=Usuario", headers=auth_headers)).json()
    acciones = [r["accion"] for r in log]
    assert "Crear" in acciones and "Actualizar" in acciones and "Resetear contraseña" in acciones

    # Ninguna contraseña (ni en claro ni hasheada) queda en el log
    import json as _json
    assert "secreta123" not in _json.dumps(log)
    assert "otraclave123" not in _json.dumps(log)
    upd = next(r for r in log if r["accion"] == "Actualizar")
    assert upd["cambios"] == {"rol": {"antes": "Auxiliar Contable", "despues": "Directora"}}


@pytest.mark.asyncio
async def test_auditoria_solo_admin_o_administradora(client: AsyncClient, auth_headers: dict):
    # Crear un Auxiliar y probar que no puede leer el log
    await client.post(
        "/api/v1/usuarios",
        json={"email": "aux.aud@test.com", "nombre_completo": "Aux Auditoría",
              "rol": "Auxiliar Contable", "is_active": True, "password": "password123"},
        headers=auth_headers,
    )
    login = await client.post(
        "/api/login/access-token",
        data={"username": "aux.aud@test.com", "password": "password123"},
    )
    aux_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/api/v1/auditoria", headers=aux_headers)
    assert resp.status_code == 403

    resp = await client.get("/api/v1/auditoria", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_filtros_de_listado(client: AsyncClient, auth_headers: dict):
    await _crear_producto(client, auth_headers, sku="AUD-F01")
    await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900666888", "razon_social": "Cliente Filtro"},
        headers=auth_headers,
    )

    todos = (await client.get("/api/v1/auditoria", headers=auth_headers)).json()
    # crear usuario del fixture no existe; producto + cliente = 2 registros
    assert len(todos) == 2

    solo_prod = (await client.get(
        "/api/v1/auditoria?entidad=Producto", headers=auth_headers)).json()
    assert len(solo_prod) == 1 and solo_prod[0]["entidad"] == "Producto"

    solo_crear = (await client.get(
        "/api/v1/auditoria?accion=Crear", headers=auth_headers)).json()
    assert len(solo_crear) == 2


@pytest.mark.asyncio
async def test_puc_y_centro_costo_auditados(client: AsyncClient, auth_headers: dict):
    # Cuenta PUC nueva + toggle
    resp = await client.post(
        "/api/v1/contabilidad/puc",
        json={"codigo_puc": "999901", "nombre": "Cuenta Auditada",
              "clase": "Gasto", "naturaleza": "Débito", "nivel": "Auxiliar"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    cuenta_id = resp.json()["id"]
    await client.patch(f"/api/v1/contabilidad/puc/{cuenta_id}/toggle", headers=auth_headers)

    log = (await client.get(
        "/api/v1/auditoria?entidad=PlanCuentas", headers=auth_headers)).json()
    assert [r["accion"] for r in log] == ["Desactivar", "Crear"]
    assert "999901" in log[0]["descripcion"]

    # Centro de costo nuevo + update con diff
    resp = await client.post(
        "/api/v1/contabilidad/centros-costo",
        json={"codigo": "CC-AUD", "nombre": "Centro Auditado", "tipo": "Marca"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    cc_id = resp.json()["id"]
    await client.put(
        f"/api/v1/contabilidad/centros-costo/{cc_id}",
        json={"responsable": "Leonardo"},
        headers=auth_headers,
    )

    log = (await client.get(
        "/api/v1/auditoria?entidad=CentroCosto", headers=auth_headers)).json()
    assert [r["accion"] for r in log] == ["Actualizar", "Crear"]
    assert log[0]["cambios"]["responsable"]["despues"] == "Leonardo"


@pytest.mark.asyncio
async def test_registro_guarda_la_ip_del_request(client: AsyncClient, auth_headers: dict):
    """#32: cada registro guarda la IP del request. Con ASGITransport el host
    del cliente es 'testclient' (no hay socket real), así que basta con
    verificar que el campo se pobló y viaja en la respuesta."""
    prod = await _crear_producto(client, auth_headers, sku="AUD-IP1")

    log = (await client.get(
        "/api/v1/auditoria?entidad=Producto", headers=auth_headers)).json()
    registro = next(r for r in log if r["entidad_id"] == prod["id"])
    assert "ip" in registro
    assert registro["ip"]  # no vacío: el middleware lo fijó
