from decimal import Decimal
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, extract, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import CurrentUser, AdminOrAdministradoraDep
from app.modules.ventas.models import Producto

from .models import MovimientoInventario, TipoMovimientoInventario, OrigenMovimiento
from .schemas import (
    MovimientoResponse, AjusteInventarioInput, InventarioDashboard, TopProductoValor,
)
from .service import registrar_movimiento

router = APIRouter(prefix="/api/v1/inventario", tags=["Inventario"])


def _to_response(mov: MovimientoInventario, nombre: Optional[str], sku: Optional[str]) -> MovimientoResponse:
    return MovimientoResponse(
        id=mov.id,
        producto_id=mov.producto_id,
        producto_nombre=nombre,
        producto_sku=sku,
        tipo=mov.tipo.value if hasattr(mov.tipo, "value") else mov.tipo,
        origen=mov.origen.value if hasattr(mov.origen, "value") else mov.origen,
        cantidad=mov.cantidad,
        stock_antes=mov.stock_antes,
        stock_despues=mov.stock_despues,
        costo_unitario=mov.costo_unitario,
        compra_id=mov.compra_id,
        venta_id=mov.venta_id,
        motivo=mov.motivo,
        usuario_id=mov.usuario_id,
        fecha=mov.fecha,
        created_at=mov.created_at,
    )


# ══════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=InventarioDashboard)
async def get_dashboard(_: CurrentUser, session: AsyncSession = Depends(get_db)):
    hoy = date.today()

    valor_inventario = await session.scalar(
        select(func.coalesce(func.sum(Producto.stock_actual * func.coalesce(Producto.precio_costo, 0)), 0))
        .where(Producto.activo == True)  # noqa: E712
    )

    stock_bajo = await session.scalar(
        select(func.count(Producto.id))
        .where(Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo)  # noqa: E712
    )

    movimientos_mes = await session.scalar(
        select(func.count(MovimientoInventario.id))
        .where(
            extract("year", MovimientoInventario.fecha) == hoy.year,
            extract("month", MovimientoInventario.fecha) == hoy.month,
        )
    )

    top_result = await session.execute(
        select(
            Producto.nombre,
            Producto.sku,
            (Producto.stock_actual * func.coalesce(Producto.precio_costo, 0)).label("valor"),
        )
        .where(Producto.activo == True)  # noqa: E712
        .order_by(desc("valor"))
        .limit(5)
    )
    top_productos = [
        TopProductoValor(producto=row[0], sku=row[1], valor=float(row[2] or 0))
        for row in top_result.all()
    ]

    return InventarioDashboard(
        valor_total_inventario=Decimal(str(valor_inventario or 0)),
        productos_stock_bajo=stock_bajo or 0,
        movimientos_mes=movimientos_mes or 0,
        top_productos_por_valor=top_productos,
    )


# ══════════════════════════════════════════════════════════
# MOVIMIENTOS (KARDEX)
# ══════════════════════════════════════════════════════════

@router.get("/movimientos", response_model=List[MovimientoResponse])
async def list_movimientos(
    _: CurrentUser,
    producto_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    origen: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    query = (
        select(MovimientoInventario, Producto.nombre, Producto.sku)
        .join(Producto, Producto.id == MovimientoInventario.producto_id)
        .order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc())
    )
    if producto_id:
        query = query.where(MovimientoInventario.producto_id == producto_id)
    if tipo:
        query = query.where(MovimientoInventario.tipo == tipo)
    if origen:
        query = query.where(MovimientoInventario.origen == origen)
    if fecha_desde:
        query = query.where(MovimientoInventario.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.where(MovimientoInventario.fecha <= fecha_hasta)

    result = await session.execute(query)
    return [_to_response(mov, nombre, sku) for mov, nombre, sku in result.all()]


@router.get("/movimientos/{producto_id}", response_model=List[MovimientoResponse])
async def list_movimientos_producto(
    producto_id: int,
    current: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    return await list_movimientos(current, producto_id=producto_id, session=session)


# ══════════════════════════════════════════════════════════
# AJUSTE MANUAL
# ══════════════════════════════════════════════════════════

@router.post("/ajustes", response_model=MovimientoResponse, status_code=201)
async def crear_ajuste(
    data: AjusteInventarioInput,
    current: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    producto = await session.get(Producto, data.producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    tipo = TipoMovimientoInventario.ENTRADA if data.tipo == "Entrada" else TipoMovimientoInventario.SALIDA

    # Un ajuste de salida no puede dejar stock negativo (ventas y devoluciones
    # ya validan; este era el único camino que permitía negativo en silencio)
    if tipo == TipoMovimientoInventario.SALIDA:
        disponible = producto.stock_actual if producto.stock_actual is not None else Decimal("0")
        if data.cantidad > disponible:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para el ajuste: disponible {disponible}, "
                       f"salida solicitada {data.cantidad}",
            )

    mov = await registrar_movimiento(
        session,
        producto_id=data.producto_id,
        tipo=tipo,
        origen=OrigenMovimiento.AJUSTE_MANUAL,
        cantidad=data.cantidad,
        motivo=data.motivo or f"Ajuste manual de {data.tipo.lower()}",
        usuario_id=current.id,
    )
    await session.commit()
    await session.refresh(mov)
    return _to_response(mov, producto.nombre, producto.sku)
