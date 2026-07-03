"""
Motor de asientos contables (partida doble automática).

Verifica que confirmar ventas/compras y abonar cartera genere asientos
balanceados con el mapeo PUC borrador, y que anular genere el reverso.
"""
import pytest
from httpx import AsyncClient

ASIENTOS = "/api/v1/contabilidad/asientos"


async def _setup_venta(client, headers, *, confirmar=True, retiene_iva=False):
    """Cliente + producto con stock + venta (opcionalmente confirmada)."""
    cli = (await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900100200", "razon_social": "Cliente Asiento SAS", "retiene_iva": retiene_iva},
        headers=headers,
    )).json()
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "AST-001", "nombre": "Biocida", "marca": "Superozono",
              "precio_venta": "100000", "stock_actual": 50},
        headers=headers,
    )).json()
    venta = (await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": "2026-07-01",
            "cliente_id": cli["id"],
            "detalles": [{"producto_id": prod["id"], "cantidad": "2", "precio_unitario": "100000.00"}],
        },
        headers=headers,
    )).json()
    if confirmar:
        resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=headers)
        assert resp.status_code == 200, resp.text
    return venta


async def _setup_compra(client, headers, *, confirmar=True):
    prov = (await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "800100200", "razon_social": "Proveedor Asiento Ltda"},
        headers=headers,
    )).json()
    compra = (await client.post(
        "/api/v1/compras/",
        json={
            "fecha": "2026-07-01",
            "proveedor_id": prov["id"],
            "retefuente": "12500.00",
            "detalles": [{"descripcion": "Insumo", "cantidad": "10", "precio_unitario": "50000.00"}],
        },
        headers=headers,
    )).json()
    if confirmar:
        resp = await client.post(f"/api/v1/compras/{compra['id']}/confirmar", headers=headers)
        assert resp.status_code == 200, resp.text
    return compra


def _saldo_por_cuenta(asiento):
    return {m["cuenta_codigo"]: (float(m["debito"]), float(m["credito"])) for m in asiento["movimientos"]}


@pytest.mark.asyncio
async def test_confirmar_venta_genera_asiento_balanceado(client: AsyncClient, auth_headers: dict):
    venta = await _setup_venta(client, auth_headers)

    resp = await client.get(f"{ASIENTOS}?documento_ref={venta['numero']}", headers=auth_headers)
    assert resp.status_code == 200
    asientos = resp.json()
    assert len(asientos) == 1
    asiento = asientos[0]

    # Partida doble balanceada
    assert float(asiento["total_debito"]) == float(asiento["total_credito"])
    assert asiento["modulo_origen"] == "ventas"
    assert asiento["tipo_documento"] == "Factura de venta"

    # Mapeo: DB Clientes por el total / CR Ingresos por base + CR IVA
    cuentas = _saldo_por_cuenta(asiento)
    assert cuentas["130505"] == (238000.0, 0.0)   # total con IVA 19%
    assert cuentas["413595"] == (0.0, 200000.0)   # base gravable
    assert cuentas["240801"] == (0.0, 38000.0)    # IVA generado


@pytest.mark.asyncio
async def test_venta_con_reteiva_incluye_cuenta_retencion(client: AsyncClient, auth_headers: dict):
    venta = await _setup_venta(client, auth_headers, retiene_iva=True)

    resp = await client.get(f"{ASIENTOS}?documento_ref={venta['numero']}", headers=auth_headers)
    asiento = resp.json()[0]
    cuentas = _saldo_por_cuenta(asiento)

    # ReteIVA 15% del IVA (38000) = 5700 → activo a favor 135517
    assert cuentas["135517"] == (5700.0, 0.0)
    # Clientes recibe el total neto (238000 - 5700)
    assert cuentas["130505"] == (232300.0, 0.0)
    assert float(asiento["total_debito"]) == float(asiento["total_credito"])


@pytest.mark.asyncio
async def test_anular_venta_genera_reverso(client: AsyncClient, auth_headers: dict):
    venta = await _setup_venta(client, auth_headers)
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.get(f"{ASIENTOS}?documento_ref={venta['numero']}", headers=auth_headers)
    asientos = resp.json()
    assert len(asientos) == 2

    reverso = next(a for a in asientos if a["descripcion"].startswith("REVERSO"))
    original = next(a for a in asientos if not a["descripcion"].startswith("REVERSO"))
    assert original["reversado"] is True

    # El reverso es el espejo exacto: netean a cero por cuenta
    orig = _saldo_por_cuenta(original)
    rev = _saldo_por_cuenta(reverso)
    for codigo, (deb, cred) in orig.items():
        assert rev[codigo] == (cred, deb)


@pytest.mark.asyncio
async def test_confirmar_compra_genera_asiento_con_retenciones(client: AsyncClient, auth_headers: dict):
    compra = await _setup_compra(client, auth_headers)

    resp = await client.get(f"{ASIENTOS}?documento_ref={compra['numero']}", headers=auth_headers)
    asiento = resp.json()[0]
    cuentas = _saldo_por_cuenta(asiento)

    # base 500000, IVA 95000, retefuente 12500 → total 582500
    assert cuentas["143501"] == (500000.0, 0.0)   # inventario
    assert cuentas["240802"] == (95000.0, 0.0)    # IVA descontable
    assert cuentas["220501"] == (0.0, 582500.0)   # proveedores
    assert cuentas["236540"] == (0.0, 12500.0)    # retefuente practicada
    assert float(asiento["total_debito"]) == float(asiento["total_credito"]) == 595000.0


@pytest.mark.asyncio
async def test_anular_compra_genera_reverso(client: AsyncClient, auth_headers: dict):
    compra = await _setup_compra(client, auth_headers)
    resp = await client.post(f"/api/v1/compras/{compra['id']}/anular", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.get(f"{ASIENTOS}?documento_ref={compra['numero']}", headers=auth_headers)
    asientos = resp.json()
    assert len(asientos) == 2
    assert any(a["descripcion"].startswith("REVERSO") for a in asientos)


@pytest.mark.asyncio
async def test_abonos_generan_asientos_de_caja(client: AsyncClient, auth_headers: dict):
    # Venta confirmada → CxC automática → abono → asiento RC
    venta = await _setup_venta(client, auth_headers)
    cxc = next(
        c for c in (await client.get("/api/v1/contabilidad/cartera/cxc", headers=auth_headers)).json()
        if c["numero_factura"] == venta["numero"]
    )
    abono = (await client.post(
        f"/api/v1/contabilidad/cartera/cxc/{cxc['id']}/abonar",
        json={"valor": "100000.00"},
        headers=auth_headers,
    )).json()

    resp = await client.get(
        f"{ASIENTOS}?documento_ref={abono['pago']['numero_comprobante']}", headers=auth_headers
    )
    asiento = resp.json()[0]
    cuentas = _saldo_por_cuenta(asiento)
    assert cuentas["110505"] == (100000.0, 0.0)  # Caja
    assert cuentas["130505"] == (0.0, 100000.0)  # Clientes
    assert asiento["tipo_documento"] == "Recibo de Caja"

    # Compra confirmada → CxP → abono → asiento CE
    compra = await _setup_compra(client, auth_headers)
    cxp = next(
        c for c in (await client.get("/api/v1/contabilidad/cartera/cxp", headers=auth_headers)).json()
        if c["numero_documento"] == compra["numero"]
    )
    abono = (await client.post(
        f"/api/v1/contabilidad/cartera/cxp/{cxp['id']}/abonar",
        json={"valor": "50000.00"},
        headers=auth_headers,
    )).json()

    resp = await client.get(
        f"{ASIENTOS}?documento_ref={abono['pago']['numero_comprobante']}", headers=auth_headers
    )
    asiento = resp.json()[0]
    cuentas = _saldo_por_cuenta(asiento)
    assert cuentas["220501"] == (50000.0, 0.0)   # Proveedores
    assert cuentas["110505"] == (0.0, 50000.0)   # Caja
    assert asiento["tipo_documento"] == "Comprobante de Egreso"


@pytest.mark.asyncio
async def test_listado_y_detalle_de_asientos(client: AsyncClient, auth_headers: dict):
    await _setup_venta(client, auth_headers)
    await _setup_compra(client, auth_headers)

    # Filtro por módulo
    resp = await client.get(f"{ASIENTOS}?modulo_origen=ventas", headers=auth_headers)
    assert len(resp.json()) == 1
    resp = await client.get(f"{ASIENTOS}?modulo_origen=compras", headers=auth_headers)
    assert len(resp.json()) == 1

    # Detalle por id
    asiento_id = resp.json()[0]["id"]
    resp = await client.get(f"{ASIENTOS}/{asiento_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["movimientos"]) >= 3

    resp = await client.get(f"{ASIENTOS}/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_motor_crea_cuentas_puc_faltantes(client: AsyncClient, auth_headers: dict):
    """La BD de test arranca sin PUC: el motor crea las cuentas del mapeo."""
    await _setup_venta(client, auth_headers)

    resp = await client.get("/api/v1/contabilidad/puc/130505", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Clientes nacionales"
    assert resp.json()["clase"] == "Activo"


@pytest.mark.asyncio
async def test_asientos_materializan_terceros(client: AsyncClient, auth_headers: dict):
    """Cada cliente/proveedor que participa en un asiento queda en el registro de terceros."""
    await _setup_venta(client, auth_headers)     # cliente NIT 900100200
    await _setup_compra(client, auth_headers)    # proveedor NIT 800100200

    resp = await client.get("/api/v1/contabilidad/terceros", headers=auth_headers)
    terceros = {t["nit_cc"]: t["tipo"] for t in resp.json()}
    assert terceros.get("900100200") == "Cliente"
    assert terceros.get("800100200") == "Proveedor"

    # Los movimientos del asiento llevan el tercero vinculado
    asientos = (await client.get(f"{ASIENTOS}?modulo_origen=ventas", headers=auth_headers)).json()
    assert all(m["cuenta_codigo"] for m in asientos[0]["movimientos"])


@pytest.mark.asyncio
async def test_tercero_cliente_y_proveedor_queda_mixto(client: AsyncClient, auth_headers: dict):
    """Un NIT que compra Y vende pasa a tipo Mixto."""
    # Cliente y proveedor con el MISMO NIT
    await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "900555000", "razon_social": "Empresa Mixta SAS"},
        headers=auth_headers,
    )
    prod = (await client.post(
        "/api/v1/ventas/productos",
        json={"sku": "MIX-1", "nombre": "P", "marca": "M", "precio_venta": "1000", "stock_actual": 10},
        headers=auth_headers,
    )).json()
    cliente_id = (await client.get("/api/v1/ventas/clientes", headers=auth_headers)).json()[0]["id"]
    venta = (await client.post(
        "/api/v1/ventas/",
        json={"fecha": "2026-07-01", "cliente_id": cliente_id,
              "detalles": [{"producto_id": prod["id"], "cantidad": "1", "precio_unitario": "1000"}]},
        headers=auth_headers,
    )).json()
    await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)

    prov = (await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "900555000", "razon_social": "Empresa Mixta SAS"},
        headers=auth_headers,
    )).json()
    compra = (await client.post(
        "/api/v1/compras/",
        json={"fecha": "2026-07-01", "proveedor_id": prov["id"],
              "detalles": [{"descripcion": "X", "cantidad": "1", "precio_unitario": "500"}]},
        headers=auth_headers,
    )).json()
    await client.post(f"/api/v1/compras/{compra['id']}/confirmar", headers=auth_headers)

    resp = await client.get("/api/v1/contabilidad/terceros", headers=auth_headers)
    tercero = next(t for t in resp.json() if t["nit_cc"] == "900555000")
    assert tercero["tipo"] == "Mixto"


@pytest.mark.asyncio
async def test_periodo_cerrado_bloquea_operaciones(client: AsyncClient, auth_headers: dict):
    """15b: con el período del mes CERRADO no se puede confirmar, abonar ni anular."""
    BASE_CONT = "/api/v1/contabilidad"

    # Crear y CERRAR el período 2026-07
    periodo = (await client.post(
        f"{BASE_CONT}/periodos", json={"anio": 2026, "mes": 7}, headers=auth_headers
    )).json()
    await client.patch(f"{BASE_CONT}/periodos/{periodo['id']}/toggle", headers=auth_headers)

    # Confirmar una venta fechada en julio → 400 y la venta sigue en Borrador
    venta = await _setup_venta(client, auth_headers, confirmar=False)
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 400
    assert "CERRADO" in resp.json()["detail"]
    resp = await client.get(f"/api/v1/ventas/{venta['id']}", headers=auth_headers)
    assert resp.json()["estado"] == "Borrador"

    # El rollback también revirtió el descuento de stock
    productos = (await client.get("/api/v1/ventas/productos", headers=auth_headers)).json()
    assert float(productos[0]["stock_actual"]) == 50.0

    # Confirmar compra en julio → 400
    compra = await _setup_compra(client, auth_headers, confirmar=False)
    resp = await client.post(f"/api/v1/compras/{compra['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 400

    # Reabrir el período → ahora sí se puede confirmar y anular
    await client.patch(f"{BASE_CONT}/periodos/{periodo['id']}/toggle", headers=auth_headers)
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)
    assert resp.status_code == 200

    # Cerrar de nuevo: anular (reverso en julio) también queda bloqueado
    await client.patch(f"{BASE_CONT}/periodos/{periodo['id']}/toggle", headers=auth_headers)
    resp = await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)
    assert resp.status_code == 400
    resp = await client.get(f"/api/v1/ventas/{venta['id']}", headers=auth_headers)
    assert resp.json()["estado"] == "Confirmada"  # la anulación no ocurrió


@pytest.mark.asyncio
async def test_mes_sin_periodo_creado_no_bloquea(client: AsyncClient, auth_headers: dict):
    """Si el mes no tiene PeriodoContable, las operaciones fluyen normal."""
    venta = await _setup_venta(client, auth_headers)  # julio sin período creado
    assert venta["numero"].startswith("SOG-V-")


@pytest.mark.asyncio
async def test_auxiliar_por_tercero_estado_de_cuenta(client: AsyncClient, auth_headers: dict):
    """15d: el auxiliar del cliente refleja factura y abono con saldo corrido."""
    venta = await _setup_venta(client, auth_headers)  # total 238000 → DB 130505
    cxc = next(
        c for c in (await client.get("/api/v1/contabilidad/cartera/cxc", headers=auth_headers)).json()
        if c["numero_factura"] == venta["numero"]
    )
    await client.post(
        f"/api/v1/contabilidad/cartera/cxc/{cxc['id']}/abonar",
        json={"valor": "100000.00"},
        headers=auth_headers,
    )

    tercero = next(
        t for t in (await client.get("/api/v1/contabilidad/terceros", headers=auth_headers)).json()
        if t["nit_cc"] == "900100200"
    )

    # Auxiliar completo del tercero
    resp = await client.get(
        f"/api/v1/contabilidad/terceros/{tercero['id']}/auxiliar", headers=auth_headers
    )
    assert resp.status_code == 200
    aux = resp.json()
    assert aux["razon_social"] == "Cliente Asiento SAS"
    assert len(aux["movimientos"]) > 0

    # Filtrado a la cuenta Clientes (130505): factura +238000, abono −100000
    resp = await client.get(
        f"/api/v1/contabilidad/terceros/{tercero['id']}/auxiliar?cuenta=130505",
        headers=auth_headers,
    )
    aux = resp.json()
    assert len(aux["movimientos"]) == 2
    assert float(aux["movimientos"][0]["debito"]) == 238000.0
    assert float(aux["movimientos"][1]["credito"]) == 100000.0
    # Saldo del auxiliar == saldo pendiente de la CxC
    assert float(aux["saldo_final"]) == 138000.0
    assert float(aux["movimientos"][-1]["saldo_acumulado"]) == 138000.0

    resp = await client.get(
        "/api/v1/contabilidad/terceros/99999/auxiliar", headers=auth_headers
    )
    assert resp.status_code == 404
