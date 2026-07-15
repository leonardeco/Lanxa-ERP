"""
Lógica de dominio del inventario — actualizar stock + registrar el movimiento
en el mismo paso atómico. Importado desde compras/router.py y ventas/router.py
para generar movimientos automáticos al confirmar/anular documentos.

#12: el producto se carga con `SELECT … FOR UPDATE` para serializar escritores
concurrentes (multi-worker / Postgres). En SQLite el FOR UPDATE es no-op, pero
el camino de código es el mismo.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ventas.models import Producto
from .models import MovimientoInventario, TipoMovimientoInventario, OrigenMovimiento

_ENTRADAS = (TipoMovimientoInventario.ENTRADA, TipoMovimientoInventario.AJUSTE_POSITIVO)


class StockError(ValueError):
    """Stock insuficiente u otra regla de inventario (mensaje apto para el usuario)."""


async def registrar_movimiento(
    session: AsyncSession,
    *,
    producto_id: int,
    tipo: TipoMovimientoInventario,
    origen: OrigenMovimiento,
    cantidad: Decimal,
    motivo: Optional[str] = None,
    usuario_id: Optional[int] = None,
    compra_id: Optional[int] = None,
    compra_detalle_id: Optional[int] = None,
    venta_id: Optional[int] = None,
    venta_detalle_id: Optional[int] = None,
    costo_unitario: Optional[Decimal] = None,
    lote_id: Optional[int] = None,
    permitir_stock_negativo: bool = False,
) -> MovimientoInventario:
    """
    Registra un movimiento de inventario y actualiza Producto.stock_actual.
    No hace commit — el caller controla la transacción (igual que el resto
    de operaciones de compras/ventas, que commitean una sola vez al final).

    Bloquea la fila del producto (`FOR UPDATE`) antes de leer/escribir stock.
    Por defecto las salidas no permiten stock negativo (evita sobreventa
    concurrente aunque el caller no re-valide).
    """
    producto = await session.scalar(
        select(Producto).where(Producto.id == producto_id).with_for_update()
    )
    if not producto:
        raise ValueError(f"Producto {producto_id} no encontrado")

    stock_antes = producto.stock_actual if producto.stock_actual is not None else Decimal("0")
    delta = Decimal(cantidad)  # se conserva la cantidad fraccionaria (sin redondear)
    stock_despues = stock_antes + delta if tipo in _ENTRADAS else stock_antes - delta

    if (
        tipo not in _ENTRADAS
        and not permitir_stock_negativo
        and stock_despues < 0
    ):
        raise StockError(
            f"Stock insuficiente para '{producto.nombre}': "
            f"disponible {stock_antes}, requerido {delta}."
        )

    producto.stock_actual = stock_despues

    mov = MovimientoInventario(
        producto_id=producto_id,
        tipo=tipo,
        origen=origen,
        cantidad=cantidad,
        stock_antes=stock_antes,
        stock_despues=stock_despues,
        costo_unitario=costo_unitario,
        compra_id=compra_id,
        compra_detalle_id=compra_detalle_id,
        venta_id=venta_id,
        venta_detalle_id=venta_detalle_id,
        lote_id=lote_id,
        motivo=motivo,
        usuario_id=usuario_id,
    )
    session.add(mov)
    await session.flush()
    return mov
