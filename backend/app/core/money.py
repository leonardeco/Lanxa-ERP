"""
Utilidades de redondeo monetario (COP, 2 decimales).

#24 — la política de redondeo de *retenciones* es configurable vía
`RETENCION_REDONDEO` en Settings:
  - half_even (default): banker's rounding, `round()` de Python / Decimal
  - half_up: redondeo comercial "hacia arriba en 0.5" (ROUND_HALF_UP)

No inventa la política contable: el Contador elige el valor en `.env`.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
from typing import Literal

RedondeoMode = Literal["half_even", "half_up"]

_QUANT = Decimal("0.01")
_MODES = {
    "half_even": ROUND_HALF_EVEN,
    "half_up": ROUND_HALF_UP,
}


def redondear_cop(
    valor: Decimal | float | int | str,
    modo: str = "half_even",
) -> Decimal:
    """Redondea a 2 decimales con la política indicada (`half_even` | `half_up`)."""
    d = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    key: RedondeoMode = "half_up" if str(modo).strip().lower() == "half_up" else "half_even"
    return d.quantize(_QUANT, rounding=_MODES[key])
