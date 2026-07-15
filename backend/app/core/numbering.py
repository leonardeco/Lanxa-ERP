"""
Numeración secuencial de documentos (SOG-V-0001, SOG-CP-0001, RC-0001, CE-0001, …).

Usa la tabla `document_sequences` con PK (tenant_id, prefix) y bloqueo de fila
(`SELECT … FOR UPDATE`) para evitar races multi-writer (#12a) y colisiones entre
tenants (Run 2).
"""

from __future__ import annotations

import re

from sqlalchemy import ForeignKey, Integer, String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.tenancy import get_tenant_id

_SUFFIX_RE = re.compile(r"(\d+)$")
_MAX_RETRIES = 5


class DocumentSequence(Base):
    """Contador monotónico por tenant + prefijo de documento."""

    __tablename__ = "document_sequences"
    __table_args__ = {"extend_existing": True}

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    prefix: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


async def _max_suffix_from_column(
    session: AsyncSession, column, prefijo: str
) -> int:
    rows = (
        await session.execute(select(column).where(column.like(f"{prefijo}-%")))
    ).scalars().all()
    max_num = 0
    for n in rows:
        m = _SUFFIX_RE.search(n or "")
        if m:
            max_num = max(max_num, int(m.group(1)))
    return max_num


async def next_sequential_numero(
    session: AsyncSession, column, prefijo: str, padding: int = 4
) -> str:
    """Devuelve el siguiente número '<prefijo>-NNNN' (scoped al tenant actual)."""
    if not prefijo or not str(prefijo).strip():
        raise ValueError("prefijo de numeración vacío")

    tenant_id = get_tenant_id()
    last_error: Exception | None = None

    for _ in range(_MAX_RETRIES):
        try:
            async with session.begin_nested():
                stmt = (
                    select(DocumentSequence)
                    .where(
                        DocumentSequence.tenant_id == tenant_id,
                        DocumentSequence.prefix == prefijo,
                    )
                    .with_for_update()
                )
                row = await session.scalar(stmt)

                if row is None:
                    seed = await _max_suffix_from_column(session, column, prefijo)
                    row = DocumentSequence(
                        tenant_id=tenant_id, prefix=prefijo, last_value=seed
                    )
                    session.add(row)
                    await session.flush()

                row.last_value += 1
                await session.flush()
                return f"{prefijo}-{row.last_value:0{padding}d}"
        except IntegrityError as exc:
            last_error = exc
            continue

    raise RuntimeError(
        f"No se pudo asignar número para prefijo {prefijo!r} (tenant={tenant_id})"
    ) from last_error
