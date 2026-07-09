"""
Capa 2 lote+vencimiento: servicio entrada_lote + consumir_fefo.
Verifica la invariante stock_actual == Σ lotes y el orden FEFO.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, func

from app.modules.ventas.models import Producto
from app.modules.inventario.models import Lote, OrigenMovimiento
from app.modules.inventario.lotes import entrada_lote, consumir_fefo, LoteError


async def _prod(db, sku):
    p = Producto(sku=sku, nombre="Aceite Ozonizado", marca="Superozono",
                 categoria="Coadyuvante", unidad_medida="Litro",
                 controla_lote=True, stock_actual=Decimal("0"))
    db.add(p)
    await db.flush()
    return p


async def _suma_lotes(db, producto_id):
    return (await db.execute(
        select(func.coalesce(func.sum(Lote.cantidad_actual), 0))
        .where(Lote.producto_id == producto_id))).scalar()


async def _entrada(db, p, cant, codigo, venc):
    return await entrada_lote(
        db, producto_id=p.id, cantidad=Decimal(cant), codigo_lote=codigo,
        fecha_vencimiento=venc, origen=OrigenMovimiento.COMPRA,
        costo_unitario=Decimal("3000"))


@pytest.mark.asyncio
async def test_entrada_crea_lote_y_sube_stock(db_session):
    p = await _prod(db_session, "LS-1")
    lote, mov = await _entrada(db_session, p, "100", "L1", date(2027, 6, 30))
    await db_session.commit()
    assert lote.cantidad_actual == Decimal("100")
    assert p.stock_actual == Decimal("100")
    assert mov.lote_id == lote.id
    assert await _suma_lotes(db_session, p.id) == Decimal("100")


@pytest.mark.asyncio
async def test_entrada_mismo_codigo_incrementa(db_session):
    p = await _prod(db_session, "LS-2")
    await _entrada(db_session, p, "10", "X", date(2027, 1, 1))
    await _entrada(db_session, p, "5", "X", date(2027, 1, 1))
    await db_session.commit()
    lotes = (await db_session.execute(
        select(Lote).where(Lote.producto_id == p.id))).scalars().all()
    assert len(lotes) == 1 and lotes[0].cantidad_actual == Decimal("15")
    assert p.stock_actual == Decimal("15")


@pytest.mark.asyncio
async def test_fefo_consume_el_que_vence_antes(db_session):
    p = await _prod(db_session, "LS-3")
    await _entrada(db_session, p, "30", "A", date(2027, 12, 1))   # vence después
    await _entrada(db_session, p, "20", "B", date(2027, 3, 1))    # vence antes
    await db_session.flush()

    movs = await consumir_fefo(db_session, producto_id=p.id,
                               cantidad=Decimal("25"), origen=OrigenMovimiento.VENTA)
    await db_session.commit()

    a = (await db_session.execute(
        select(Lote).where(Lote.producto_id == p.id, Lote.codigo_lote == "A"))).scalar_one()
    b = (await db_session.execute(
        select(Lote).where(Lote.producto_id == p.id, Lote.codigo_lote == "B"))).scalar_one()
    assert b.cantidad_actual == Decimal("0") and b.activo is False  # se agotó el que vence antes
    assert a.cantidad_actual == Decimal("25")                       # quedó 30-5
    assert p.stock_actual == Decimal("25")                          # 50-25
    assert await _suma_lotes(db_session, p.id) == Decimal("25")     # invariante
    assert len(movs) == 2


@pytest.mark.asyncio
async def test_fefo_salta_vencidos(db_session):
    p = await _prod(db_session, "LS-4")
    ayer = date.today() - timedelta(days=1)
    await _entrada(db_session, p, "10", "VENC", ayer)
    await _entrada(db_session, p, "10", "OK", date.today() + timedelta(days=200))
    await db_session.flush()

    movs = await consumir_fefo(db_session, producto_id=p.id,
                               cantidad=Decimal("10"), origen=OrigenMovimiento.VENTA)
    await db_session.commit()

    venc = (await db_session.execute(
        select(Lote).where(Lote.producto_id == p.id, Lote.codigo_lote == "VENC"))).scalar_one()
    ok = (await db_session.execute(
        select(Lote).where(Lote.producto_id == p.id, Lote.codigo_lote == "OK"))).scalar_one()
    assert venc.cantidad_actual == Decimal("10")   # intacto: no se despacha vencido
    assert ok.cantidad_actual == Decimal("0")
    assert len(movs) == 1


@pytest.mark.asyncio
async def test_fefo_insuficiente_no_vencido_lanza(db_session):
    p = await _prod(db_session, "LS-5")
    ayer = date.today() - timedelta(days=1)
    await _entrada(db_session, p, "100", "V", ayer)                      # todo vencido
    await _entrada(db_session, p, "5", "OK", date.today() + timedelta(days=100))
    await db_session.flush()
    with pytest.raises(LoteError):
        await consumir_fefo(db_session, producto_id=p.id,
                            cantidad=Decimal("10"), origen=OrigenMovimiento.VENTA)
