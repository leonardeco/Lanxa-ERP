"""Política de contraseñas (core + endpoints de alta/cambio)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.passwords import PasswordPolicyError, validate_password_policy


def test_validate_password_ok():
    assert validate_password_policy("claveSegura1") == "claveSegura1"
    assert validate_password_policy("Abcd1234") == "Abcd1234"


@pytest.mark.parametrize(
    "pwd,fragmento",
    [
        ("corta", "8"),
        ("sinumeroaa", "dígito"),
        ("12345678", "letra"),
        ("Admin2026!", "no está permitida"),
        ("password1", "no está permitida"),
    ],
)
def test_validate_password_rechaza(pwd: str, fragmento: str):
    with pytest.raises(PasswordPolicyError) as exc:
        validate_password_policy(pwd)
    assert fragmento.lower() in str(exc.value).lower()


@pytest.mark.asyncio
async def test_crear_usuario_rechaza_password_debil(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.post(
        "/api/v1/usuarios/",
        headers=auth_headers,
        json={
            "email": "debil@test.com",
            "nombre_completo": "Debil",
            "rol": "Auxiliar",
            "is_active": True,
            "password": "sololetras",
        },
    )
    assert resp.status_code == 422, resp.text
    body = resp.text.lower()
    assert "dígito" in body or "digito" in body or "password" in body


@pytest.mark.asyncio
async def test_crear_usuario_rechaza_password_fabrica(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.post(
        "/api/v1/usuarios/",
        headers=auth_headers,
        json={
            "email": "fabrica@test.com",
            "nombre_completo": "Fabrica",
            "rol": "Auxiliar",
            "is_active": True,
            "password": "Admin2026!",
        },
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_cambio_password_rechaza_solo_letras(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.put(
        "/api/v1/usuarios/me/password",
        headers=auth_headers,
        json={"current_password": "testpassword", "new_password": "sololetras"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_onboard_rechaza_password_debil(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.post(
        "/api/v1/tenants/onboard",
        headers=auth_headers,
        json={
            "codigo": "weak-co",
            "razon_social": "Weak Co",
            "admin_email": "admin@weak-co.test",
            "admin_nombre": "Admin Weak",
            "admin_password": "sinnumero",
        },
    )
    assert resp.status_code == 422, resp.text
