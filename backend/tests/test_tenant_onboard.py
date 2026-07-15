"""Run 5 — onboarding multi-empresa + uniques por tenant."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.tenancy import Tenant, DEFAULT_TENANT_ID, apply_rls_tenant, set_tenant_id, reset_tenant_id
from app.modules.usuarios.models import Usuario


@pytest.mark.asyncio
async def test_onboard_crea_tenant_y_admin(
    client: AsyncClient, auth_headers: dict, db_session
):
    r = await client.post(
        "/api/v1/tenants/onboard",
        headers=auth_headers,
        json={
            "codigo": "demo-co",
            "razon_social": "Demo Company SAS",
            "nit": "900111222",
            "admin_email": "admin@demo-co.test",
            "admin_nombre": "Admin Demo",
            "admin_password": "DemoPass123!",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["tenant"]["codigo"] == "demo-co"
    assert body["admin_email"] == "admin@demo-co.test"
    tid = body["tenant"]["id"]
    assert tid != DEFAULT_TENANT_ID

    # Login del nuevo admin
    login = await client.post(
        "/api/login/access-token",
        data={"username": "admin@demo-co.test", "password": "DemoPass123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    me = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "admin@demo-co.test"
    assert me.json()["rol"] == "Superusuario"

    # No puede onboardear (no es plataforma)
    denied = await client.post(
        "/api/v1/tenants/onboard",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "codigo": "otra",
            "razon_social": "Otra",
            "admin_email": "a@otra.test",
            "admin_nombre": "A",
            "admin_password": "Password1!",
        },
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_onboard_codigo_duplicado(client: AsyncClient, auth_headers: dict):
    payload = {
        "codigo": "dup-co",
        "razon_social": "Dup",
        "admin_email": "a1@dup.test",
        "admin_nombre": "A1",
        "admin_password": "Password1!",
    }
    r1 = await client.post("/api/v1/tenants/onboard", headers=auth_headers, json=payload)
    assert r1.status_code == 201, r1.text
    payload["admin_email"] = "a2@dup.test"
    r2 = await client.post("/api/v1/tenants/onboard", headers=auth_headers, json=payload)
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_mismo_sku_en_dos_tenants_ok(db_session):
    """Tras uniques compuestos, el mismo SKU puede existir en dos tenants."""
    from decimal import Decimal
    from app.modules.ventas.models import Producto

    db_session.add(Tenant(id=2, codigo="sku-t2", razon_social="T2", activo=True))
    await db_session.flush()

    set_tenant_id(1)
    await apply_rls_tenant(db_session, 1)
    db_session.add(Producto(
        sku="SHARED", nombre="P1", marca="M",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=1,
    ))
    await db_session.flush()

    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    db_session.add(Producto(
        sku="SHARED", nombre="P2", marca="M",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=2,
    ))
    await db_session.commit()
    reset_tenant_id()
