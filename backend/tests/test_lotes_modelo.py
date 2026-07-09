"""
Capa 1 lote+vencimiento: flag controla_lote, modelo Lote y lote_id en el kardex.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.ventas.models import Producto
from app.modules.inventario.models import (
    Lote, MovimientoInventario, TipoMovimientoInventario, OrigenMovimiento,
)


def _producto(sku, controla_lote=False):
    return Producto(sku=sku, nombre="Aceite Ozonizado", marca="Superozono",
                    categoria="Coadyuvante", unidad_medida="Litro",
                    controla_lote=controla_lote)


@pytest.mark.asyncio
async def test_controla_lote_default_false(db_session):
    p = _producto("LOT-P1")
    db_session.add(p)
    await db_session.commit()
    assert p.controla_lote is False


@pytest.mark.asyncio
async def test_crear_lote_y_kardex_con_lote(db_session):
    p = _producto("LOT-P2", controla_lote=True)
    db_session.add(p)
    await db_session.flush()

    lote = Lote(
        producto_id=p.id, codigo_lote="L-2026-001",
        fecha_vencimiento=date(2027, 6, 30),
        cantidad_actual=Decimal("100"), cantidad_inicial=Decimal("100"),
        costo_unitario=Decimal("32000"), origen="Compra",
    )
    db_session.add(lote)
    await db_session.flush()

    db_session.add(MovimientoInventario(
        producto_id=p.id, tipo=TipoMovimientoInventario.ENTRADA,
        origen=OrigenMovimiento.COMPRA, cantidad=Decimal("100"),
        stock_antes=Decimal("0"), stock_despues=Decimal("100"), lote_id=lote.id,
    ))
    await db_session.commit()

    got = (await db_session.execute(
        select(Lote).where(Lote.producto_id == p.id))).scalar_one()
    assert got.codigo_lote == "L-2026-001"
    assert got.fecha_vencimiento == date(2027, 6, 30)
    assert got.cantidad_actual == Decimal("100")
    assert got.activo is True

    mov = (await db_session.execute(
        select(MovimientoInventario).where(MovimientoInventario.lote_id == lote.id))).scalar_one()
    assert mov.lote_id == lote.id


@pytest.mark.asyncio
async def test_codigo_lote_unico_por_producto(db_session):
    p = _producto("LOT-P3", controla_lote=True)
    db_session.add(p)
    await db_session.flush()
    db_session.add(Lote(producto_id=p.id, codigo_lote="DUP",
                        cantidad_actual=Decimal("1"), cantidad_inicial=Decimal("1")))
    await db_session.commit()

    db_session.add(Lote(producto_id=p.id, codigo_lote="DUP",
                        cantidad_actual=Decimal("2"), cantidad_inicial=Decimal("2")))
    with pytest.raises(IntegrityError):
        await db_session.commit()
