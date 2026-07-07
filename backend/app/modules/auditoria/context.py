"""
IP del request actual, para el log de auditoría (#32).

Se guarda en un ContextVar que un middleware ASGI puro fija al inicio de cada
request (ver main.py). registrar_auditoria() lo lee sin tener que pasar el
Request por la firma de cada endpoint. Los ContextVar aíslan por request en
asyncio, así que no hay cruce entre peticiones concurrentes.
"""

import contextvars

_client_ip: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "client_ip", default=None
)


def set_client_ip(ip: str | None) -> None:
    _client_ip.set(ip)


def get_client_ip() -> str | None:
    return _client_ip.get()
