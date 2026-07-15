"""
Política de contraseñas (nice-to-have del backlog, LAN-friendly).

Reglas (sin contadora / sin IdP):
- mínimo 8 caracteres
- al menos una letra y un dígito
- no puede ser la contraseña de fábrica del seed (Admin2026!)

No exige símbolos ni expiración (aceptable en LAN mono-empresa).
"""

from __future__ import annotations

import re

# Debe coincidir con config._DEFAULT_SEED_ADMIN_PASSWORD / seed.
_FORBIDDEN = frozenset(
    {
        "Admin2026!",
        "admin2026!",
        "password",
        "password1",
        "12345678",
        "qwerty123",
    }
)

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


class PasswordPolicyError(ValueError):
    """Contraseña que no cumple la política (mensaje apto para HTTP 400)."""


def validate_password_policy(password: str) -> str:
    """Valida y devuelve la contraseña, o lanza PasswordPolicyError."""
    if password is None:
        raise PasswordPolicyError("La contraseña es obligatoria")
    pwd = str(password)
    if len(pwd) < 8:
        raise PasswordPolicyError("La contraseña debe tener al menos 8 caracteres")
    if len(pwd) > 128:
        raise PasswordPolicyError("La contraseña no puede superar 128 caracteres")
    if not _HAS_LETTER.search(pwd):
        raise PasswordPolicyError("La contraseña debe incluir al menos una letra")
    if not _HAS_DIGIT.search(pwd):
        raise PasswordPolicyError("La contraseña debe incluir al menos un dígito")
    if pwd in _FORBIDDEN or pwd.lower() in {f.lower() for f in _FORBIDDEN}:
        raise PasswordPolicyError("Esa contraseña no está permitida; elige otra")
    return pwd
