"""
Numeración secuencial de documentos (SOG-V-0001, SOG-CP-0001, RC-0001, CE-0001).

Centraliza la lógica que antes estaba duplicada en ventas/compras/contabilidad.
- Usa MAX del sufijo numérico existente (no COUNT, que colisiona si se borra un
  registro intermedio).
- Es tolerante a números con formato inesperado: ignora los que no terminan en
  dígitos en vez de reventar con ValueError.

Nota: bajo alta concurrencia con múltiples escritores (p. ej. PostgreSQL con varios
workers) dos requests simultáneos podrían calcular el mismo número. En el despliegue
actual (SQLite, un solo escritor) eso no ocurre. Para multi-worker, migrar a una
secuencia nativa o a una tabla contador con bloqueo de fila.
"""

import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_SUFFIX_RE = re.compile(r"(\d+)$")


async def next_sequential_numero(
    session: AsyncSession, column, prefijo: str, padding: int = 4
) -> str:
    """Devuelve el siguiente número '<prefijo>-NNNN' para la columna dada."""
    rows = (
        await session.execute(select(column).where(column.like(f"{prefijo}-%")))
    ).scalars().all()

    max_num = 0
    for n in rows:
        m = _SUFFIX_RE.search(n or "")
        if m:
            max_num = max(max_num, int(m.group(1)))

    return f"{prefijo}-{max_num + 1:0{padding}d}"
