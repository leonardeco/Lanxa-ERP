"""
Servicios de dominio de Ventas (#13).

Extrae la orquestación de confirmar/anular un documento de venta fuera del router:
movimiento de inventario (FEFO para productos con lote, stock simple para el resto),
Cuenta por Cobrar automática y asiento contable (partida doble). El router queda
delgado: valida la transición de estado, delega aquí y traduce `VentaError` a un
HTTP 400.

Convención transaccional (igual que `inventario/service.py` y `inventario/lotes.py`):
estas funciones **hacen flush, no commit** — el caller (la dependencia `get_db`)
controla la transacción y commitea una sola vez al final del request.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ventas.models import (
    VentaDocumento, VentaDetalle, EstadoVenta, DevolucionVenta,
)
from app.modules.ventas.models import Producto, Cliente
from app.modules.contabilidad.models import CuentaPorCobrar, EstadoDocumento
from app.modules.contabilidad.asientos import (
    asiento_venta_confirmada, reversar_asientos,
)
from app.modules.inventario.service import registrar_movimiento, StockError
from app.modules.inventario.models import TipoMovimientoInventario, OrigenMovimiento
from app.modules.inventario.lotes import consumir_fefo, revertir_por_lotes, LoteError


class VentaError(ValueError):
    """Error de regla de negocio de una venta (mensaje apto para el usuario).

    El router lo traduce a HTTP 400."""


async def _detalles(db: AsyncSession, venta_id: int) -> list[VentaDetalle]:
    return list((await db.execute(
        select(VentaDetalle).where(VentaDetalle.venta_id == venta_id)
    )).scalars().all())


async def confirmar_venta(db: AsyncSession, venta: VentaDocumento, usuario) -> None:
    """Confirma una venta en Borrador: valida stock, descuenta inventario (FEFO en
    productos con lote), crea la CxC automática y genera el asiento. Precondición:
    `venta.estado == BORRADOR` (la valida el caller)."""
    detalles = await _detalles(db, venta.id)

    # #12: bloquear productos en orden de id (evita deadlock entre ventas
    # concurrentes) y validar stock con la fila ya bloqueada.
    prod_ids = sorted({d.producto_id for d in detalles})
    prods: dict[int, Producto] = {}
    for pid in prod_ids:
        prod = await db.scalar(
            select(Producto).where(Producto.id == pid).with_for_update()
        )
        if prod is not None:
            prods[pid] = prod

    faltantes = []
    for d in detalles:
        prod = prods.get(d.producto_id)
        disponible = prod.stock_actual if (prod and prod.stock_actual is not None) else Decimal("0")
        if disponible < d.cantidad:
            nombre = prod.nombre if prod else f"Producto {d.producto_id}"
            faltantes.append(f"{nombre} (disponible: {disponible}, requerido: {d.cantidad})")
    if faltantes:
        raise VentaError("Stock insuficiente para confirmar la venta: " + "; ".join(faltantes))

    venta.estado = EstadoVenta.CONFIRMADA

    # Salidas de inventario: FEFO para productos con lote, stock simple para el resto
    for d in detalles:
        prod = prods.get(d.producto_id)
        if prod and prod.controla_lote:
            try:
                await consumir_fefo(
                    db,
                    producto_id=d.producto_id,
                    cantidad=d.cantidad,
                    origen=OrigenMovimiento.VENTA,
                    usuario_id=usuario.id,
                    venta_id=venta.id,
                    venta_detalle_id=d.id,
                    motivo=f"Salida por venta {venta.numero}",
                )
            except LoteError as exc:
                raise VentaError(str(exc))
        else:
            try:
                await registrar_movimiento(
                    db,
                    producto_id=d.producto_id,
                    tipo=TipoMovimientoInventario.SALIDA,
                    origen=OrigenMovimiento.VENTA,
                    cantidad=d.cantidad,
                    motivo=f"Salida por venta {venta.numero}",
                    usuario_id=usuario.id,
                    venta_id=venta.id,
                    venta_detalle_id=d.id,
                )
            except StockError as exc:
                raise VentaError(str(exc))

    # CxC automática (espejo de compras→CxP), idempotente
    existing_cxc = await db.scalar(
        select(CuentaPorCobrar).where(CuentaPorCobrar.numero_factura == venta.numero)
    )
    if not existing_cxc:
        cliente = await db.get(Cliente, venta.cliente_id)
        db.add(CuentaPorCobrar(
            numero_factura=venta.numero,
            fecha_emision=venta.fecha,
            cliente_nit=(cliente.nit_cc if cliente else ""),
            nombre_cliente=(cliente.razon_social if cliente else None),
            valor_factura=venta.total,
            abonos=Decimal("0.00"),
            fecha_vencimiento=venta.fecha_vencimiento,
            estado=EstadoDocumento.PENDIENTE,
            notas=f"Generada automáticamente por venta {venta.numero}",
        ))

    # Asiento contable automático (partida doble)
    await asiento_venta_confirmada(db, venta, usuario_id=usuario.id)

    await db.flush()


async def anular_venta(db: AsyncSession, venta: VentaDocumento, usuario) -> None:
    """Anula una venta: revierte inventario y CxC y reversa el asiento. Precondición:
    `venta.estado != ANULADA` (la valida el caller). Lanza `VentaError` si la venta
    tiene notas crédito o su CxC ya tiene abonos."""
    # BUG-007: con notas crédito no se puede anular (duplicaría el reingreso de stock)
    tiene_nc = await db.scalar(
        select(DevolucionVenta.id).where(DevolucionVenta.venta_id == venta.id).limit(1)
    )
    if tiene_nc:
        raise VentaError(
            "La venta tiene notas crédito asociadas y no se puede anular. "
            "El saldo ya fue ajustado por las devoluciones."
        )

    # BUG-008: si la CxC ya tiene abonos, primero se anulan los pagos en Cartera
    cxc = await db.scalar(
        select(CuentaPorCobrar).where(CuentaPorCobrar.numero_factura == venta.numero)
    )
    if cxc and (cxc.abonos or Decimal("0")) > 0:
        raise VentaError(
            "La factura tiene abonos registrados. Anula primero los pagos "
            "en Cartera y vuelve a intentar."
        )

    estado_anterior = venta.estado
    venta.estado = EstadoVenta.ANULADA

    # La CxC generada al confirmar también se anula
    if cxc and cxc.estado != EstadoDocumento.ANULADO:
        cxc.estado = EstadoDocumento.ANULADO
        cxc.notas = ((cxc.notas or "") + f"\n[ANULADA] junto con la venta {venta.numero}").strip()

    # Revertir las salidas de inventario si la venta ya las había generado
    if estado_anterior in (EstadoVenta.CONFIRMADA, EstadoVenta.FACTURADA):
        for d in await _detalles(db, venta.id):
            prod = await db.get(Producto, d.producto_id)
            if prod and prod.controla_lote:
                await revertir_por_lotes(
                    db,
                    producto_id=d.producto_id,
                    cantidad=d.cantidad,
                    tipo_reverso=TipoMovimientoInventario.ENTRADA,
                    origen=OrigenMovimiento.REVERSO_VENTA,
                    venta_id=venta.id,
                    venta_detalle_id=d.id,
                    motivo=f"Reverso por anulación de venta {venta.numero}",
                    usuario_id=usuario.id,
                )
            else:
                await registrar_movimiento(
                    db,
                    producto_id=d.producto_id,
                    tipo=TipoMovimientoInventario.ENTRADA,
                    origen=OrigenMovimiento.REVERSO_VENTA,
                    cantidad=d.cantidad,
                    motivo=f"Reverso por anulación de venta {venta.numero}",
                    usuario_id=usuario.id,
                    venta_id=venta.id,
                    venta_detalle_id=d.id,
                )

    # Reverso del asiento contable si la venta ya lo había generado
    await reversar_asientos(
        db, documento_ref=venta.numero, usuario_id=usuario.id,
        motivo=f"Anulación de venta {venta.numero}",
    )

    await db.flush()
