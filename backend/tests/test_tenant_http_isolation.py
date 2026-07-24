"""Run 4 — aislamiento HTTP: listados no devuelven filas de otro tenant."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import get_password_hash
from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    apply_rls_tenant,
    set_tenant_id,
    reset_tenant_id,
)
from app.modules.usuarios.models import Usuario
from app.modules.ventas.models import Cliente, Producto, VentaDetalle, VentaDocumento
from app.modules.ventas_diarias.models import VentaDiaria, VentaDiariaDetalle


@pytest.mark.asyncio
async def test_list_productos_no_ve_otro_tenant(
    client: AsyncClient, auth_headers: dict, db_session
):
    """Admin del tenant 1 no ve productos del tenant 2 vía GET /productos."""
    db_session.add(Tenant(id=2, codigo="otra-co", razon_social="Otra CO", activo=True))
    await db_session.flush()

    # Producto visible (tenant 1) — se crea vía API para respetar flujo real
    r_ok = await client.post(
        "/api/v1/ventas/productos",
        headers=auth_headers,
        json={
            "sku": "T1-HTTP",
            "nombre": "Producto tenant 1",
            "marca": "Test",
            "precio_venta": "1000",
            "stock_actual": 10,
        },
    )
    assert r_ok.status_code == 201, r_ok.text

    # Producto de otro tenant (inserción directa + GUC/context)
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    db_session.add(
        Producto(
            sku="T2-SECRET",
            nombre="No debe verse",
            marca="X",
            precio_venta=Decimal("1"),
            precio_costo=Decimal("1"),
            stock_actual=Decimal("0"),
            tenant_id=2,
        )
    )
    await db_session.commit()
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)

    listed = await client.get("/api/v1/ventas/productos", headers=auth_headers)
    assert listed.status_code == 200, listed.text
    skus = {p["sku"] for p in listed.json()}
    assert "T1-HTTP" in skus
    assert "T2-SECRET" not in skus


@pytest.mark.asyncio
async def test_get_producto_otro_tenant_404(
    client: AsyncClient, auth_headers: dict, db_session
):
    db_session.add(Tenant(id=2, codigo="otra2", razon_social="Otra2", activo=True))
    await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    p = Producto(
        sku="T2-HIDDEN",
        nombre="Hidden",
        marca="X",
        precio_venta=Decimal("1"),
        stock_actual=Decimal("0"),
        tenant_id=2,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    other_id = p.id
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)

    r = await client.get(f"/api/v1/ventas/productos/{other_id}", headers=auth_headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_usuarios_solo_mismo_tenant(
    client: AsyncClient, auth_headers: dict, db_session
):
    db_session.add(Tenant(id=2, codigo="otra3", razon_social="Otra3", activo=True))
    await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    db_session.add(
        Usuario(
            email="admin@otra.com",
            nombre_completo="Admin Otra",
            rol="Superusuario",
            hashed_password=get_password_hash("password123"),
            tenant_id=2,
            is_active=True,
        )
    )
    await db_session.commit()
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)

    r = await client.get("/api/v1/usuarios", headers=auth_headers)
    assert r.status_code == 200, r.text
    emails = {u["email"] for u in r.json()}
    assert "admin@test.com" in emails
    assert "admin@otra.com" not in emails


@pytest.mark.asyncio
async def test_list_ventas_diarias_no_ve_otro_tenant(
    client: AsyncClient, auth_headers: dict, db_session
):
    """Auxiliar del tenant 1 no ve ventas diarias del tenant 2."""
    db_session.add(Tenant(id=2, codigo="peru-test", razon_social="Peru Test", activo=True))
    await db_session.flush()

    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    producto = Producto(
        sku="PE-SECRET", nombre="Secreto", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=2,
    )
    cliente = Cliente(nit_cc="99999999", razon_social="Cliente Secreto", tenant_id=2)
    db_session.add_all([producto, cliente])
    await db_session.flush()
    venta = VentaDiaria(
        fecha=date(2026, 1, 1), cliente_id=cliente.id, tenant_id=2,
    )
    db_session.add(venta)
    await db_session.flush()
    db_session.add(VentaDiariaDetalle(
        venta_diaria_id=venta.id, producto_id=producto.id,
        cantidad=Decimal("1"), venta=Decimal("100"), saldo=Decimal("100"),
        tenant_id=2,
    ))
    await db_session.commit()
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)

    r = await client.get("/api/v1/ventas-diarias/", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert all(v["cliente_id"] != cliente.id for v in r.json())
    detalle_producto_ids = {
        d["producto_id"] for v in r.json() for d in v["detalles"]
    }
    assert producto.id not in detalle_producto_ids  # ninguna linea del tenant 2 debe aparecer


@pytest.mark.asyncio
async def test_dashboard_ventas_no_cuenta_otro_tenant(
    client: AsyncClient, auth_headers: dict, db_session
):
    """El dashboard de Ventas (conteos y ventas por marca) no debe incluir
    datos de otro tenant — ni siquiera como agregados/conteos."""
    db_session.add(Tenant(id=2, codigo="dash-test", razon_social="Dash Test", activo=True))
    await db_session.flush()

    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    producto = Producto(
        sku="T2-DASH", nombre="Producto tenant 2", marca="MarcaSecretaT2",
        precio_venta=Decimal("500000"), precio_costo=Decimal("1"),
        stock_actual=Decimal("10"), tenant_id=2,
    )
    cliente = Cliente(nit_cc="88888888", razon_social="Cliente tenant 2", tenant_id=2)
    db_session.add_all([producto, cliente])
    await db_session.flush()
    venta = VentaDocumento(
        numero="T2-V-0001", cliente_id=cliente.id, total=Decimal("500000.00"),
        tenant_id=2,
    )
    db_session.add(venta)
    await db_session.flush()
    db_session.add(VentaDetalle(
        venta_id=venta.id, producto_id=producto.id,
        precio_unitario=Decimal("500000"), total_linea=Decimal("500000.00"),
        tenant_id=2,
    ))
    await db_session.commit()
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)

    r = await client.get("/api/v1/ventas/dashboard", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cantidad_ventas_mes"] == 0
    assert float(data["ventas_mes_actual"]) == 0.0
    assert data["total_clientes_activos"] == 0
    assert data["total_productos_activos"] == 0
    assert all(row["marca"] != "MarcaSecretaT2" for row in data["ventas_por_marca"])
