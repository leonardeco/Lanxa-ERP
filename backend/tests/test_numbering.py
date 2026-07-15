"""Tests de numeración secuencial (#12a) — contador con bloqueo de fila."""

from __future__ import annotations

import pytest
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.numbering import DocumentSequence, next_sequential_numero


class _DocStub(Base):
    """Tabla mínima solo para tests de siembra desde MAX(columna)."""

    __tablename__ = "test_doc_stub_numbering"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(40), nullable=False)


@pytest.mark.asyncio
async def test_next_sequential_empieza_en_1(db_session):
    n1 = await next_sequential_numero(db_session, _DocStub.numero, "SOG-V")
    n2 = await next_sequential_numero(db_session, _DocStub.numero, "SOG-V")
    assert n1 == "SOG-V-0001"
    assert n2 == "SOG-V-0002"


@pytest.mark.asyncio
async def test_next_sequential_siembra_desde_max_existente(db_session):
    db_session.add(_DocStub(numero="SOG-V-0007"))
    db_session.add(_DocStub(numero="SOG-V-0003"))
    await db_session.flush()

    n = await next_sequential_numero(db_session, _DocStub.numero, "SOG-V")
    assert n == "SOG-V-0008"


@pytest.mark.asyncio
async def test_prefijos_independientes(db_session):
    a = await next_sequential_numero(db_session, _DocStub.numero, "RC")
    b = await next_sequential_numero(db_session, _DocStub.numero, "CE")
    c = await next_sequential_numero(db_session, _DocStub.numero, "RC")
    assert a == "RC-0001"
    assert b == "CE-0001"
    assert c == "RC-0002"


@pytest.mark.asyncio
async def test_prefijo_vacio_falla(db_session):
    with pytest.raises(ValueError, match="vacío"):
        await next_sequential_numero(db_session, _DocStub.numero, "  ")


@pytest.mark.asyncio
async def test_document_sequence_persiste_last_value(db_session):
    await next_sequential_numero(db_session, _DocStub.numero, "COT")
    await next_sequential_numero(db_session, _DocStub.numero, "COT")
    row = await db_session.scalar(
        select(DocumentSequence).where(DocumentSequence.prefix == "COT")
    )
    assert row is not None
    assert row.last_value == 2
