"""
Super Ozono Global — Cliente HTTP para la API de Alegra
Documentación: https://developer.alegra.com/
Auth: Basic Auth con email:token en base64
"""

import base64
import httpx
from app.core.config import get_settings

settings = get_settings()

ALEGRA_BASE = "https://api.alegra.com/api/v1"


def _auth_header() -> str:
    raw = f"{settings.ALEGRA_EMAIL}:{settings.ALEGRA_TOKEN}"
    return "Basic " + base64.b64encode(raw.encode()).decode()


def _headers() -> dict:
    return {
        "Authorization": _auth_header(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def alegra_get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{ALEGRA_BASE}{path}", headers=_headers(), params=params or {})
        r.raise_for_status()
        return r.json()


async def alegra_post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{ALEGRA_BASE}{path}", headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()


async def alegra_put(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.put(f"{ALEGRA_BASE}{path}", headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()
