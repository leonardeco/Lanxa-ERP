"""
Utilidades de tiempo del proyecto.

Todas las columnas DateTime del ERP guardan UTC naive (sin tzinfo), por lo
que el reemplazo de datetime.utcnow() —deprecado en Python 3.12— debe seguir
devolviendo un datetime naive para no mezclar valores aware/naive en la BD
ni en comparaciones.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")


def utcnow() -> datetime:
    """UTC actual como datetime naive (compatible con columnas DateTime sin timezone).

    Usar para campos técnicos (created_at, expiración de tokens)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def bogota_now() -> datetime:
    """Hora local del negocio (America/Bogota, UTC-5 sin DST) como datetime naive.

    Usar para fechas de NEGOCIO (comprobantes de pago, kardex): un abono a las
    8pm en Colombia debe quedar fechado ese día, no el siguiente en UTC."""
    return datetime.now(BOGOTA).replace(tzinfo=None)
