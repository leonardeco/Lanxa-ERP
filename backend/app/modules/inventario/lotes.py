"""
Servicio de lotes (Capa 2 del módulo lote+vencimiento).

Entradas con lote y consumo FEFO (First-Expired-First-Out), manteniendo la
invariante `producto.stock_actual == Σ lotes.cantidad_actual` para productos con
`controla_lote=True`. No hace commit — el caller controla la transacción, igual
que `registrar_movimiento` (que es quien mueve el stock agregado + el kardex).
"""

from datetime import date, timedelta
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
    compra_id: int | None = None,
    compra_detalle_id: int | None = None,
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
            compra_id=compra_id,
            compra_detalle_id=compra_detalle_id,
            lote_id=lote.id,
        )
        movimientos.append(mov)
        restante = restante - tomar

    return movimientos


async def revertir_por_lotes(
    db: AsyncSession,
    *,
    producto_id: int,
    cantidad: Decimal,
    tipo_reverso: TipoMovimientoInventario,
    origen: OrigenMovimiento,
    compra_id: int | None = None,
    compra_detalle_id: int | None = None,
    venta_id: int | None = None,
    venta_detalle_id: int | None = None,
    motivo: str | None = None,
    usuario_id: int | None = None,
) -> list[MovimientoInventario]:
    """Aplica `cantidad` en sentido inverso sobre los lotes que tocaron los
    movimientos originales de un renglón de documento, manteniendo la invariante
    `stock_actual == Σ lotes`. Un movimiento de kardex por lote tocado. Sin commit.

    - `tipo_reverso=ENTRADA` → **reingreso de una salida** (anular/devolución de
      venta): reincrementa los lotes que la salida original consumió, del más
      reciente al más antiguo, con tope por lote = lo que esa salida tomó de él.
    - `tipo_reverso=SALIDA` → **reverso de una entrada** (anular/devolución de
      compra): descuenta de los lotes que la entrada original creó; si ya no
      alcanzan (se vendieron entre tanto), toma el resto por FEFO.
    """
    restante = Decimal(cantidad)
    if restante <= 0:
        return []

    cond = [
        MovimientoInventario.producto_id == producto_id,
        MovimientoInventario.lote_id.is_not(None),
    ]
    if compra_detalle_id is not None:
        cond.append(MovimientoInventario.compra_detalle_id == compra_detalle_id)
    if venta_detalle_id is not None:
        cond.append(MovimientoInventario.venta_detalle_id == venta_detalle_id)

    originales = (await db.execute(
        select(MovimientoInventario).where(*cond)
        .order_by(MovimientoInventario.id.desc())
    )).scalars().all()

    es_reingreso = tipo_reverso in (
        TipoMovimientoInventario.ENTRADA, TipoMovimientoInventario.AJUSTE_POSITIVO,
    )
    movimientos: list[MovimientoInventario] = []

    for orig in originales:
        if restante <= 0:
            break
        lote = await db.get(Lote, orig.lote_id)
        if lote is None:
            continue
        if es_reingreso:
            # No restaurar más de lo que esa salida tomó de este lote.
            tomar = orig.cantidad if orig.cantidad < restante else restante
            lote.cantidad_actual = lote.cantidad_actual + tomar
            lote.activo = True
        else:
            # Reverso de entrada: sólo lo que quede en el lote.
            if lote.cantidad_actual <= 0:
                continue
            tomar = lote.cantidad_actual if lote.cantidad_actual < restante else restante
            lote.cantidad_actual = lote.cantidad_actual - tomar
            if lote.cantidad_actual == 0:
                lote.activo = False
        mov = await registrar_movimiento(
            db,
            producto_id=producto_id,
            tipo=tipo_reverso,
            origen=origen,
            cantidad=tomar,
            motivo=motivo,
            usuario_id=usuario_id,
            compra_id=compra_id,
            compra_detalle_id=compra_detalle_id,
            venta_id=venta_id,
            venta_detalle_id=venta_detalle_id,
            lote_id=lote.id,
        )
        movimientos.append(mov)
        restante = restante - tomar

    # Reverso de entrada cuyos lotes ya se habían agotado: el resto sale por FEFO.
    if restante > 0 and not es_reingreso:
        movimientos.extend(await consumir_fefo(
            db,
            producto_id=producto_id,
            cantidad=restante,
            origen=origen,
            usuario_id=usuario_id,
            compra_id=compra_id,
            compra_detalle_id=compra_detalle_id,
            motivo=motivo,
            permitir_vencidos=True,
        ))

    return movimientos


# ── Consulta / alertas de vencimiento (Capa 4) ──────────────────────────────

DIAS_ALERTA_DEFAULT = 30


def estado_lote(fecha_vencimiento: date | None, hoy: date, dias_alerta: int) -> str:
    """Clasifica un lote por su vencimiento: sin_vencimiento / vencido /
    por_vencer (dentro de `dias_alerta`) / vigente."""
    if fecha_vencimiento is None:
        return "sin_vencimiento"
    if fecha_vencimiento < hoy:
        return "vencido"
    if fecha_vencimiento <= hoy + timedelta(days=dias_alerta):
        return "por_vencer"
    return "vigente"


def dias_para_vencer(fecha_vencimiento: date | None, hoy: date) -> int | None:
    """Días hasta el vencimiento (negativo si ya venció). None si el lote no vence."""
    if fecha_vencimiento is None:
        return None
    return (fecha_vencimiento - hoy).days
