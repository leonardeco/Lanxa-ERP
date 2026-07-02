"""
Utilidades de tiempo del proyecto.

Todas las columnas DateTime del ERP guardan UTC naive (sin tzinfo), por lo
que el reemplazo de datetime.utcnow() —deprecado en Python 3.12— debe seguir
devolviendo un datetime naive para no mezclar valores aware/naive en la BD
ni en comparaciones.
"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """UTC actual como datetime naive (compatible con columnas DateTime sin timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
