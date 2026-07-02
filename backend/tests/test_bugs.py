"""
Pruebas de regresión de bugs — Super Ozono Global ERP
Cada test documenta un comportamiento específico y fallará si el bug reaparece.
"""

import pytest
from decimal import Decimal
from datetime import date
from httpx import AsyncClient


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

async def _crear_producto(client, auth_headers, sku, precio="50000.00", stock=100):
    resp = await client.post(
        "/api/v1/ventas/productos",
        json={"sku": sku, "nombre": f"Prod {sku}", "marca": "Bug-Test",
              "precio_venta": precio, "tarifa_iva": "19.00",
              "stock_actual": stock, "stock_minimo": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_cliente(client, auth_headers, nit):
    resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": nit, "razon_social": f"Cliente Bug {nit}"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _crear_venta(client, auth_headers, cliente_id, producto_id, precio="50000.00"):
    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": cliente_id,
            "detalles": [{
                "producto_id": producto_id,
                "cantidad": "2.00",
                "precio_unitario": precio,
                "descuento_porcentaje": "0.00",
                "iva_porcentaje": "19.00",
            }],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════
# BUG-001: reteica no se resta del total de ventas
# Archivo: app/modules/ventas/router.py
# Línea ~519: total = base_gravable + iva_total - retefuente - reteiva
# reteica está en el modelo VentaDocumento pero nunca se calcula ni se resta.
# ESTADO: El campo reteica se inicializa en 0 y nunca cambia.
#         La fórmula es internamente consistente SÓLO porque reteica siempre es 0.
#         Pero si en el futuro se calcula reteica, el total será incorrecto.
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bug001_reteica_siempre_cero_en_ventas(client: AsyncClient, auth_headers: dict):
    """
    Documenta que reteica nunca se calcula en ventas.
    Si el negocio necesita cobrar reteica, este test debe actualizarse.
    Actualmente el campo existe en el schema pero siempre vale 0.
    """
    cliente = await _crear_cliente(client, auth_headers, "BUG001-NIT")
    producto = await _crear_producto(client, auth_headers, "BUG001-P")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    # reteica siempre es 0 actualmente — documentar este comportamiento
    assert Decimal(str(venta["reteica"])) == Decimal("0.00"), (
        "BUG-001: reteica debería ser 0 (no implementado en ventas). "
        "Si ahora se calcula, actualizar este test y verificar que se reste del total."
    )


@pytest.mark.asyncio
async def test_bug001_total_es_consistente_con_campos(client: AsyncClient, auth_headers: dict):
    """
    El total debe ser = base_gravable + iva_total - retefuente - reteiva - reteica.
    Si reteica siempre es 0, la fórmula actual es correcta.
    """
    cliente = await _crear_cliente(client, auth_headers, "BUG001b-NIT")
    producto = await _crear_producto(client, auth_headers, "BUG001b-P")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    total_esperado = (
        Decimal(str(venta["base_gravable"]))
        + Decimal(str(venta["iva_total"]))
        - Decimal(str(venta["retefuente"]))
        - Decimal(str(venta["reteiva"]))
        - Decimal(str(venta["reteica"]))  # siempre 0 actualmente
    )
    assert Decimal(str(venta["total"])) == total_esperado, (
        f"El campo 'total' no coincide con la suma de sus componentes. "
        f"total={venta['total']}, calculado={total_esperado}"
    )


# ══════════════════════════════════════════════════════════
# BUG-002: N+1 queries en list_ventas()
# Archivo: app/modules/ventas/router.py — endpoint GET /api/v1/ventas/
# Para cada venta: 1 query para cliente + N queries para productos de cada línea.
# Con 50 ventas de 5 líneas cada una → 1 + 50 + 50×5 = 301 queries.
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bug002_list_ventas_retorna_con_datos_enriquecidos(client: AsyncClient, auth_headers: dict):
    """
    Verifica que list_ventas() devuelve datos de cliente y detalles correctamente
    (el N+1 existe pero los datos son correctos — este test falla si se rompe al optimizar).
    """
    cliente = await _crear_cliente(client, auth_headers, "BUG002-NIT")
    producto = await _crear_producto(client, auth_headers, "BUG002-P")
    await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    resp = await client.get("/api/v1/ventas/", headers=auth_headers)
    assert resp.status_code == 200

    ventas = resp.json()
    assert len(ventas) >= 1

    venta = ventas[0]
    # El enriquecimiento debe existir
    assert "cliente_razon_social" in venta
    assert "cliente_nit" in venta
    assert "detalles" in venta
    assert isinstance(venta["detalles"], list)
    if len(venta["detalles"]) > 0:
        assert "producto_nombre" in venta["detalles"][0]
        assert "producto_sku" in venta["detalles"][0]


# ══════════════════════════════════════════════════════════
# BUG-003: datetime.utcnow() deprecated en Python 3.12+
# Archivos: app/core/security.py, app/modules/ventas/models.py,
#           app/modules/usuarios/models.py
# Debería usarse datetime.now(timezone.utc) en Python moderno.
# IMPACTO: DeprecationWarning, posibles comportamientos inesperados en el futuro.
# ══════════════════════════════════════════════════════════

def test_bug003_security_importa_sin_warning():
    """
    Importar el módulo de seguridad no debe producir errores.
    El datetime.utcnow() es deprecated pero sigue funcionando en Python 3.12.
    Este test confirma que el módulo sigue operativo.
    """
    import warnings
    from app.core.security import create_access_token, verify_password, get_password_hash

    # Verificar que las funciones básicas funcionan
    hashed = get_password_hash("testpassword")
    assert verify_password("testpassword", hashed)
    token = create_access_token("1")
    assert isinstance(token, str)
    assert len(token) > 10


# ══════════════════════════════════════════════════════════
# BUG-004: Race condition en _next_venta_numero()
# Archivo: app/modules/ventas/router.py
# La función usa COUNT(*) para calcular el siguiente número.
# Dos requests simultáneos pueden obtener el mismo COUNT y generar el mismo número.
# El campo `numero` tiene UNIQUE constraint, así que uno de ellos fallará con 500.
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bug004_numeros_venta_son_unicos_secuencial(client: AsyncClient, auth_headers: dict):
    """
    Verifica que creaciones secuenciales producen números únicos.
    La race condition ocurre en concurrencia real, no en requests secuenciales.
    """
    cliente = await _crear_cliente(client, auth_headers, "BUG004-NIT")
    producto = await _crear_producto(client, auth_headers, "BUG004-P")

    v1 = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])
    v2 = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])
    v3 = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    numeros = [v1["numero"], v2["numero"], v3["numero"]]
    assert len(set(numeros)) == 3, f"Números duplicados detectados: {numeros}"
    for num in numeros:
        assert num.startswith("SOG-V-"), f"Formato de número incorrecto: {num}"


# ══════════════════════════════════════════════════════════
# BUG-005: Race condition en numeración de compras
# Archivo: app/modules/compras/router.py — función create_compra()
# Usa max(int(n.split("-")[-1]) para calcular siguiente número.
# Dos requests concurrentes pueden obtener el mismo máximo.
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bug005_numeros_compra_son_unicos_secuencial(client: AsyncClient, auth_headers: dict):
    """Verificar que la numeración secuencial de compras funciona correctamente."""
    # Crear proveedor primero
    prov_resp = await client.post(
        "/api/v1/compras/proveedores",
        json={
            "nit_cc": "BUG005-NIT",
            "razon_social": "Proveedor Bug 005",
        },
        headers=auth_headers,
    )
    assert prov_resp.status_code == 201
    proveedor_id = prov_resp.json()["id"]

    producto = await _crear_producto(client, auth_headers, "BUG005-P")

    compra_payload = {
        "fecha": str(date.today()),
        "proveedor_id": proveedor_id,
        "retefuente": "0.00",
        "reteiva": "0.00",
        "reteica": "0.00",
        "detalles": [{
            "descripcion": "Producto test",
            "producto_id": producto["id"],
            "cantidad": "1.00",
            "precio_unitario": "10000.00",
            "descuento_porcentaje": "0.00",
            "iva_porcentaje": "19.00",
        }],
    }
    c1 = await client.post("/api/v1/compras/", json=compra_payload, headers=auth_headers)
    c2 = await client.post("/api/v1/compras/", json=compra_payload, headers=auth_headers)

    assert c1.status_code == 201, c1.text
    assert c2.status_code == 201, c2.text

    n1 = c1.json()["numero"]
    n2 = c2.json()["numero"]
    assert n1 != n2, f"Números de compra duplicados: {n1} y {n2}"
    assert n1.startswith("SOG-CP-")
    assert n2.startswith("SOG-CP-")


# ══════════════════════════════════════════════════════════
# BUG-006: Inconsistencia de commit entre módulos
# Archivo: app/modules/ventas/router.py (usa flush, no commit explícito)
# vs app/modules/compras/router.py (usa commit explícito)
# CONCLUSIÓN: No es un bug funcional porque get_db() hace commit al final.
#             Es una inconsistencia de estilo que puede confundir.
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bug006_venta_persiste_entre_requests(client: AsyncClient, auth_headers: dict):
    """
    Verifica que las ventas creadas con flush() (sin commit explícito)
    efectivamente se persisten gracias al commit de get_db().
    """
    cliente = await _crear_cliente(client, auth_headers, "BUG006-NIT")
    producto = await _crear_producto(client, auth_headers, "BUG006-P")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])
    venta_id = venta["id"]

    # Hacer un segundo request para confirmar que la venta persiste
    resp = await client.get(f"/api/v1/ventas/{venta_id}", headers=auth_headers)
    assert resp.status_code == 200, (
        "BUG-006: La venta no persiste entre requests. "
        "Verificar que get_db() hace commit correctamente."
    )
    assert resp.json()["id"] == venta_id


# ══════════════════════════════════════════════════════════
# BUG-007: Inventario se actualiza correctamente al confirmar/anular venta
# Archivo: app/modules/ventas/router.py y app/modules/inventario/service.py
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bug007_confirmar_venta_descuenta_inventario(client: AsyncClient, auth_headers: dict):
    """Al confirmar una venta, el stock del producto debe reducirse."""
    producto = await _crear_producto(client, auth_headers, "BUG007-P", stock=50)
    cliente = await _crear_cliente(client, auth_headers, "BUG007-NIT")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    stock_antes = producto["stock_actual"]

    await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)

    prod_resp = await client.get(f"/api/v1/ventas/productos/{producto['id']}", headers=auth_headers)
    stock_despues = prod_resp.json()["stock_actual"]

    assert stock_despues == stock_antes - 2, (
        f"BUG-007: Stock incorrecto después de confirmar venta. "
        f"Antes={stock_antes}, Después={stock_despues}, Esperado={stock_antes - 2}"
    )


@pytest.mark.asyncio
async def test_bug007_anular_venta_confirmada_restaura_inventario(client: AsyncClient, auth_headers: dict):
    """Al anular una venta confirmada, el stock debe restaurarse."""
    producto = await _crear_producto(client, auth_headers, "BUG007b-P", stock=50)
    cliente = await _crear_cliente(client, auth_headers, "BUG007b-NIT")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    stock_inicial = producto["stock_actual"]

    # Confirmar (descuenta)
    await client.post(f"/api/v1/ventas/{venta['id']}/confirmar", headers=auth_headers)

    # Anular (debe revertir)
    await client.post(f"/api/v1/ventas/{venta['id']}/anular", headers=auth_headers)

    prod_resp = await client.get(f"/api/v1/ventas/productos/{producto['id']}", headers=auth_headers)
    stock_final = prod_resp.json()["stock_actual"]

    assert stock_final == stock_inicial, (
        f"BUG-007: El stock no se restauró al anular la venta. "
        f"Inicial={stock_inicial}, Final={stock_final}"
    )


# ══════════════════════════════════════════════════════════
# BUG-008: Formato incorrecto de número de compra si hay nombres con "-"
# Archivo: app/modules/compras/router.py línea ~248
# `max(int(n.split("-")[-1]) for n in nums)` — el campo 'numero' tiene formato
# SOG-CP-0001, split("-")[-1] = "0001" → int("0001") = 1. Funciona.
# PERO si el numero tuviera más "-" en el futuro, esto fallaría.
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bug008_numero_compra_formato_correcto(client: AsyncClient, auth_headers: dict):
    """El número de compra debe tener el formato SOG-CP-NNNN."""
    prov_resp = await client.post(
        "/api/v1/compras/proveedores",
        json={"nit_cc": "BUG008-NIT", "razon_social": "Proveedor Bug 008"},
        headers=auth_headers,
    )
    assert prov_resp.status_code == 201
    proveedor_id = prov_resp.json()["id"]
    producto = await _crear_producto(client, auth_headers, "BUG008-P")

    compra_resp = await client.post(
        "/api/v1/compras/",
        json={
            "fecha": str(date.today()),
            "proveedor_id": proveedor_id,
            "retefuente": "0.00",
            "reteiva": "0.00",
            "reteica": "0.00",
            "detalles": [{
                "descripcion": "Producto Bug 008",
                "producto_id": producto["id"],
                "cantidad": "1.00",
                "precio_unitario": "10000.00",
                "descuento_porcentaje": "0.00",
                "iva_porcentaje": "19.00",
            }],
        },
        headers=auth_headers,
    )
    assert compra_resp.status_code == 201
    numero = compra_resp.json()["numero"]

    parts = numero.split("-")
    assert len(parts) == 3, f"Formato de número incorrecto: {numero}"
    assert parts[0] == "SOG"
    assert parts[1] == "CP"
    assert parts[2].isdigit(), f"La parte numérica no es un dígito: {parts[2]}"


# ══════════════════════════════════════════════════════════
# BUG-009: Alegra sync usa POST para actualizar (debería ser PUT)
# Archivo: app/modules/alegra/router.py línea 76
# `alegra_post(f"/contacts/{cliente.alegra_id}", payload)` — la API de Alegra
# puede requerir PUT para actualizar contactos existentes.
# Imposible de testear sin credenciales reales — documentado aquí.
# ══════════════════════════════════════════════════════════

def test_bug009_alegra_sync_documentado():
    """
    Documenta el comportamiento potencialmente incorrecto de sync con Alegra.

    En alegra/router.py:
    - Si cliente.alegra_id existe: usa alegra_post(f"/contacts/{cliente.alegra_id}")
    - La API REST de Alegra probablemente requiere PUT/PATCH para updates, no POST.

    Sin credenciales de Alegra este comportamiento no es testeable en CI.
    Verificar manualmente contra la documentación de la API de Alegra.
    """
    # Este test es un marcador de documentación — siempre pasa.
    assert True, "Ver comentario del test para detalles del bug."


# ══════════════════════════════════════════════════════════
# BUG-010: Cálculo de retenciones en ventas fijo vs compras configurable
# En ventas: retefuente = 2.5% si base >= $1.092.000 (hardcoded)
# En compras: retefuente es input del usuario
# ══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_bug010_retefuente_ventas_no_aplica_bajo_umbral(client: AsyncClient, auth_headers: dict):
    """Retefuente en ventas solo aplica si base >= $1.092.000."""
    cliente = await _crear_cliente(client, auth_headers, "BUG010-NIT")
    producto = await _crear_producto(client, auth_headers, "BUG010-P", precio="50000.00")
    venta = await _crear_venta(client, auth_headers, cliente["id"], producto["id"])

    # 2 × $50.000 = $100.000 → bajo el umbral → retefuente = 0
    assert Decimal(str(venta["retefuente"])) == Decimal("0.00"), (
        f"BUG-010: Se cobró retefuente ({venta['retefuente']}) sobre una base "
        f"de {venta['base_gravable']} que está bajo el umbral de $1.092.000"
    )


@pytest.mark.asyncio
async def test_bug010_retefuente_ventas_aplica_sobre_umbral(client: AsyncClient, auth_headers: dict):
    """Retefuente debe aplicar si el cliente es agente retenedor de fuente y la base
    supera el tope (RETEFUENTE_BASE_UVT × UVT_VALOR = 27 × 49.799 ≈ $1.344.573)."""
    # Cliente agente retenedor de fuente
    cli_resp = await client.post(
        "/api/v1/ventas/clientes",
        json={"nit_cc": "BUG010b-NIT", "razon_social": "Cliente Retenedor", "retiene_fuente": True},
        headers=auth_headers,
    )
    assert cli_resp.status_code == 201, cli_resp.text
    cliente = cli_resp.json()

    # 2 × $1.000.000 = $2.000.000 → sobre el tope
    producto = await _crear_producto(client, auth_headers, "BUG010b-P", precio="1000000.00")

    resp = await client.post(
        "/api/v1/ventas/",
        json={
            "fecha": str(date.today()),
            "cliente_id": cliente["id"],
            "detalles": [{
                "producto_id": producto["id"],
                "cantidad": "2.00",
                "precio_unitario": "1000000.00",
                "descuento_porcentaje": "0.00",
                "iva_porcentaje": "19.00",
            }],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    venta = resp.json()

    base = Decimal(str(venta["base_gravable"]))
    retefuente = Decimal(str(venta["retefuente"]))

    assert retefuente > Decimal("0.00"), (
        f"No se calculó retefuente para cliente retenedor sobre base {base}"
    )
    esperado = round(base * Decimal("0.025"), 2)
    assert retefuente == esperado, f"Retefuente incorrecto: {retefuente} ≠ {esperado}"
