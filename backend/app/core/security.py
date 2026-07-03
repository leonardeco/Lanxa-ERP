"""
Super Ozono Global — Funciones criptográficas y JWT
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from app.core.time import utcnow
from typing import Any, Union

import bcrypt
from jose import jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt solo usa los primeros 72 bytes de la contraseña. passlib (usado hasta
# julio 2026) truncaba en silencio; se conserva ese comportamiento explícito
# para que TODOS los hashes existentes sigan verificando igual (bcrypt >= 5
# lanzaría ValueError en vez de truncar).
_BCRYPT_MAX_BYTES = 72


def _preparar_password(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Genera un JWT para el usuario logueado."""
    if expires_delta:
        expire = utcnow() + expires_delta
    else:
        expire = utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def generate_refresh_token() -> str:
    """Token opaco aleatorio (no JWT) para usar como refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_token: str) -> str:
    """Hash del refresh token para guardarlo en BD (nunca el valor crudo)."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def refresh_token_expiry() -> datetime:
    return utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica la contraseña contra el hash bcrypt (compatible con los
    hashes $2b$ generados por passlib antes de la migración de julio 2026)."""
    try:
        return bcrypt.checkpw(_preparar_password(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        # Hash malformado/no-bcrypt en BD: credencial inválida, nunca 500
        return False


def get_password_hash(password: str) -> str:
    """Genera un hash bcrypt (cost 12, mismo factor que usaba passlib)."""
    return bcrypt.hashpw(_preparar_password(password), bcrypt.gensalt(rounds=12)).decode("utf-8")
