"""
Servicio de lotes (Capa 2 del módulo lote+vencimiento).

Entradas con lote y consumo FEFO (First-Expired-First-Out), manteniendo la
invariante `producto.stock_actual == Σ lotes.cantidad_actual` para productos con
`controla_lote=True`. No hace commit — el caller controla la transacción, igual
que `registrar_movimiento` (que es quien mueve el stock agregado + el kardex).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import bogota_now
from app.modules.inventario.models import (
    Lote, MovimientoInventario, TipoMovimientoInventario, OrigenMovimiento,
)
from app.modules.inventario.service import registrar_movimiento


class LoteError(ValueError):
    """Error de validación de una operación de lote (mensaje apto para el usuario)."""


async def entrada_lote(
    db: AsyncSession,
    *,
    producto_id: int,
    cantidad: Decimal,
    codigo_lote: str,
    fecha_vencimiento: date | None,
    origen: OrigenMovimiento,
    costo_unitario: Decimal | None = None,
    usuario_id: int | None = None,
    compra_id: int | None = None,
    compra_detalle_id: int | None = None,
    motivo: str | None = None,
) -> tuple[Lote, MovimientoInventario]:
    """Registra una entrada de stock a un lote (lo crea o lo incrementa) y su
    movimiento de kardex. Sube `stock_actual` vía registrar_movimiento."""
    cant = Decimal(cantidad)
    if cant <= 0:
        raise LoteError("La cantidad de entrada debe ser mayor a cero.")
    if not codigo_lote or not str(codigo_lote).strip():
        raise LoteError("El código de lote es obligatorio para productos con control de lote.")
    codigo = str(codigo_lote).strip()

    lote = (await db.execute(
        select(Lote).where(Lote.producto_id == producto_id, Lote.codigo_lote == codigo)
    )).scalar_one_or_none()

    if lote is None:
        lote = Lote(
            producto_id=producto_id, codigo_lote=codigo,
            fecha_vencimiento=fecha_vencimiento,
            cantidad_actual=Decimal("0"), cantidad_inicial=Decimal("0"),
            costo_unitario=costo_unitario, origen=origen.value, activo=True,
        )
        db.add(lote)
        await db.flush()
    else:
        # Mismo código = mismo lote: se incrementa. Se refresca vencimiento/costo
        # si el nuevo dato viene informado.
        if fecha_vencimiento is not None:
            lote.fecha_vencimiento = fecha_vencimiento
        if costo_unitario is not None:
            lote.costo_unitario = costo_unitario
        lote.activo = True

    lote.cantidad_actual = lote.cantidad_actual + cant
    lote.cantidad_inicial = lote.cantidad_inicial + cant

    mov = await registrar_movimiento(
        db,
        producto_id=producto_id,
        tipo=TipoMovimientoInventario.ENTRADA,
        origen=origen,
        cantidad=cant,
        motivo=motivo or f"Entrada lote {codigo}",
        usuario_id=usuario_id,
        costo_unitario=costo_unitario,
        compra_id=compra_id,
        compra_detalle_id=compra_detalle_id,
        lote_id=lote.id,
    )
    return lote, mov


async def consumir_fefo(
    db: AsyncSession,
    *,
    producto_id: int,
    cantidad: Decimal,
    origen: OrigenMovimiento,
    usuario_id: int | None = None,
    venta_id: int | None = None,
    venta_detalle_id: int | None = None,
    motivo: str | None = None,
    hoy: date | None = None,
    permitir_vencidos: bool = False,
) -> list[MovimientoInventario]:
    """Descuenta `cantidad` de los lotes del producto por FEFO (vence antes → sale
    antes; los sin vencimiento van al final). Salta los vencidos salvo
    `permitir_vencidos`. Un movimiento de kardex por cada lote tocado. Lanza
    LoteError si no hay stock (no vencido) suficiente."""
    restante = Decimal(cantidad)
    if restante <= 0:
        raise LoteError("La cantidad a consumir debe ser mayor a cero.")
    dia = hoy or bogota_now().date()

    lotes = (await db.execute(
        select(Lote)
        .where(Lote.producto_id == producto_id, Lote.activo.is_(True), Lote.cantidad_actual > 0)
        .order_by(Lote.fecha_vencimiento.is_(None), Lote.fecha_vencimiento, Lote.id)
    )).scalars().all()

    disponibles = [
        lo for lo in lotes
        if permitir_vencidos or lo.fecha_vencimiento is None or lo.fecha_vencimiento >= dia
    ]
    total = sum((lo.cantidad_actual for lo in disponibles), Decimal("0"))
    if total < restante:
        raise LoteError(
            f"Stock por lote insuficiente (no vencido): disponible {total}, requerido {restante}."
        )

    movimientos: list[MovimientoInventario] = []
    for lote in disponibles:
        if restante <= 0:
            break
        tomar = lote.cantidad_actual if lote.cantidad_actual < restante else restante
        lote.cantidad_actual = lote.cantidad_actual - tomar
        if lote.cantidad_actual == 0:
            lote.activo = False
        mov = await registrar_movimiento(
            db,
            producto_id=producto_id,
            tipo=TipoMovimientoInventario.SALIDA,
            origen=origen,
            cantidad=tomar,
            motivo=motivo or f"Salida FEFO lote {lote.codigo_lote}",
            usuario_id=usuario_id,
            venta_id=venta_id,
            venta_detalle_id=venta_detalle_id,
            lote_id=lote.id,
        )
        movimientos.append(mov)
        restante = restante - tomar

    return movimientos
