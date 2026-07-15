"""#12 — locks de stock: FOR UPDATE + rechazo de stock negativo en salidas."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.numbering import next_sequential_numero
from app.modules.inventario.models import TipoMovimientoInventario, OrigenMovimiento
from app.modules.inventario.service import registrar_movimiento, StockError
from app.modules.ventas.models import Producto


async def _producto(db, *, stock: str = "10", sku: str = "LOCK-1") -> Producto:
    p = Producto(
        sku=sku,
        nombre="Producto lock test",
        precio_venta=Decimal("1000"),
        precio_costo=Decimal("500"),
        stock_actual=Decimal(stock),
        stock_minimo=0,
        activo=True,
    )
    db.add(p)
    await db.flush()
    return p


@pytest.mark.asyncio
async def test_salida_con_lock_descuenta_stock(db_session):
    p = await _producto(db_session, stock="10")
    await registrar_movimiento(
        db_session,
        producto_id=p.id,
        tipo=TipoMovimientoInventario.SALIDA,
        origen=OrigenMovimiento.VENTA,
        cantidad=Decimal("3"),
        motivo="test",
    )
    await db_session.refresh(p)
    assert p.stock_actual == Decimal("7")


@pytest.mark.asyncio
async def test_salida_no_permite_stock_negativo(db_session):
    p = await _producto(db_session, stock="2", sku="LOCK-2")
    with pytest.raises(StockError, match="insuficiente"):
        await registrar_movimiento(
            db_session,
            producto_id=p.id,
            tipo=TipoMovimientoInventario.SALIDA,
            origen=OrigenMovimiento.VENTA,
            cantidad=Decimal("5"),
            motivo="test oversell",
        )
    await db_session.refresh(p)
    assert p.stock_actual == Decimal("2")


@pytest.mark.asyncio
async def test_entrada_sigue_sumando(db_session):
    p = await _producto(db_session, stock="1", sku="LOCK-3")
    await registrar_movimiento(
        db_session,
        producto_id=p.id,
        tipo=TipoMovimientoInventario.ENTRADA,
        origen=OrigenMovimiento.COMPRA,
        cantidad=Decimal("4"),
        motivo="test entrada",
    )
    await db_session.refresh(p)
    assert p.stock_actual == Decimal("5")


@pytest.mark.asyncio
async def test_permitir_stock_negativo_explicito(db_session):
    p = await _producto(db_session, stock="1", sku="LOCK-4")
    await registrar_movimiento(
        db_session,
        producto_id=p.id,
        tipo=TipoMovimientoInventario.SALIDA,
        origen=OrigenMovimiento.AJUSTE,
        cantidad=Decimal("3"),
        motivo="ajuste forzado",
        permitir_stock_negativo=True,
    )
    await db_session.refresh(p)
    assert p.stock_actual == Decimal("-2")
