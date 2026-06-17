from datetime import date
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import CurrentUser
from app.modules.contabilidad.models import CuentaPorCobrar, CuentaPorPagar
from app.modules.compras.models import CompraDocumento
from app.modules.ventas.models import VentaDocumento, VentaDetalle, Producto, Cliente, EstadoVenta

from .schemas import (
    AgingBucket, AgingDetalle, AgingReporte, AgingCarteraResponse,
    TotalPorGrupo, ComprasPeriodoResponse, VentasPeriodoResponse,
    RetencionesPeriodoResponse,
)

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes"])

BUCKET_ORDER = ["Corriente", "1-30", "31-60", "61-90", "+90"]


def _bucket(dias: int) -> str:
    if dias <= 0:
        return "Corriente"
    if dias <= 30:
        return "1-30"
    if dias <= 60:
        return "31-60"
    if dias <= 90:
        return "61-90"
    return "+90"


def _aging_from_rows(items) -> AgingReporte:
    """items: lista de tuplas (id, numero, tercero, nit, saldo, fecha_vencimiento)"""
    hoy = date.today()
    detalle: List[AgingDetalle] = []
    totales = {b: {"cantidad": 0, "total": Decimal("0")} for b in BUCKET_ORDER}
    total_pendiente = Decimal("0")

    for id_, numero, tercero, nit, saldo, fecha_venc in items:
        dias = (hoy - fecha_venc).days if fecha_venc else -1
        bucket = _bucket(dias)
        detalle.append(AgingDetalle(
            id=id_, numero=numero, tercero=tercero or "—", nit=nit or "—",
            saldo_pendiente=saldo, dias_vencido=dias, bucket=bucket,
            fecha_vencimiento=fecha_venc,
        ))
        totales[bucket]["cantidad"] += 1
        totales[bucket]["total"] += saldo
        total_pendiente += saldo

    detalle.sort(key=lambda d: d.dias_vencido, reverse=True)
    buckets = [
        AgingBucket(bucket=b, cantidad=totales[b]["cantidad"], total=totales[b]["total"])
        for b in BUCKET_ORDER
    ]
    return AgingReporte(buckets=buckets, detalle=detalle, total_pendiente=total_pendiente)


def _default_rango(fecha_desde: Optional[date], fecha_hasta: Optional[date]):
    hoy = date.today()
    if fecha_hasta is None:
        fecha_hasta = hoy
    if fecha_desde is None:
        fecha_desde = hoy.replace(day=1)
    return fecha_desde, fecha_hasta


def _D(x) -> Decimal:
    return Decimal(str(x or 0))


# ══════════════════════════════════════════════════════════
# AGING DE CARTERA
# ══════════════════════════════════════════════════════════

@router.get("/aging-cartera", response_model=AgingCarteraResponse)
async def aging_cartera(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    cxc_rows = (await db.execute(
        select(CuentaPorCobrar).where(CuentaPorCobrar.estado.notin_(["Pagado", "Anulado"]))
    )).scalars().all()
    cxp_rows = (await db.execute(
        select(CuentaPorPagar).where(CuentaPorPagar.estado.notin_(["Pagado", "Anulado"]))
    )).scalars().all()

    cxc_items = [
        (c.id, c.numero_factura, c.nombre_cliente, c.cliente_nit,
         (c.valor_factura or Decimal("0")) - (c.abonos or Decimal("0")), c.fecha_vencimiento)
        for c in cxc_rows
    ]
    cxp_items = [
        (p.id, p.numero_documento, p.razon_social, p.proveedor_nit,
         (p.valor or Decimal("0")) - (p.abonos or Decimal("0")), p.fecha_vencimiento)
        for p in cxp_rows
    ]

    return AgingCarteraResponse(
        cxc=_aging_from_rows(cxc_items),
        cxp=_aging_from_rows(cxp_items),
    )


# ══════════════════════════════════════════════════════════
# COMPRAS Y VENTAS POR PERÍODO
# ══════════════════════════════════════════════════════════

@router.get("/compras-periodo", response_model=ComprasPeriodoResponse)
async def compras_periodo(
    _: CurrentUser,
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    fecha_desde, fecha_hasta = _default_rango(fecha_desde, fecha_hasta)

    r = await db.execute(
        select(func.coalesce(func.sum(CompraDocumento.total), 0), func.count(CompraDocumento.id))
        .where(
            CompraDocumento.fecha.between(fecha_desde, fecha_hasta),
            CompraDocumento.estado != "Anulada",
        )
    )
    total, cantidad = r.one()

    r2 = await db.execute(
        select(
            CompraDocumento.proveedor_razon_social,
            func.sum(CompraDocumento.total).label("total"),
            func.count(CompraDocumento.id),
        )
        .where(
            CompraDocumento.fecha.between(fecha_desde, fecha_hasta),
            CompraDocumento.estado != "Anulada",
        )
        .group_by(CompraDocumento.proveedor_razon_social)
        .order_by(desc("total"))
    )
    por_proveedor = [
        TotalPorGrupo(nombre=row[0] or "—", total=float(row[1] or 0), cantidad=row[2])
        for row in r2.all()
    ]

    return ComprasPeriodoResponse(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        total=_D(total),
        cantidad_documentos=cantidad or 0,
        por_proveedor=por_proveedor,
    )


@router.get("/ventas-periodo", response_model=VentasPeriodoResponse)
async def ventas_periodo(
    _: CurrentUser,
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    fecha_desde, fecha_hasta = _default_rango(fecha_desde, fecha_hasta)

    r = await db.execute(
        select(func.coalesce(func.sum(VentaDocumento.total), 0), func.count(VentaDocumento.id))
        .where(
            VentaDocumento.fecha.between(fecha_desde, fecha_hasta),
            VentaDocumento.estado != EstadoVenta.ANULADA,
        )
    )
    total, cantidad = r.one()

    r2 = await db.execute(
        select(
            Cliente.razon_social,
            func.sum(VentaDocumento.total).label("total"),
            func.count(VentaDocumento.id),
        )
        .join(Cliente, Cliente.id == VentaDocumento.cliente_id)
        .where(
            VentaDocumento.fecha.between(fecha_desde, fecha_hasta),
            VentaDocumento.estado != EstadoVenta.ANULADA,
        )
        .group_by(Cliente.razon_social)
        .order_by(desc("total"))
    )
    por_cliente = [
        TotalPorGrupo(nombre=row[0] or "—", total=float(row[1] or 0), cantidad=row[2])
        for row in r2.all()
    ]

    r3 = await db.execute(
        select(
            Producto.marca,
            func.coalesce(func.sum(VentaDetalle.total_linea), 0).label("total"),
            func.count(VentaDetalle.id),
        )
        .join(VentaDetalle, VentaDetalle.producto_id == Producto.id)
        .join(VentaDocumento, VentaDocumento.id == VentaDetalle.venta_id)
        .where(
            VentaDocumento.fecha.between(fecha_desde, fecha_hasta),
            VentaDocumento.estado != EstadoVenta.ANULADA,
        )
        .group_by(Producto.marca)
        .order_by(desc("total"))
    )
    por_marca = [
        TotalPorGrupo(nombre=row[0] or "—", total=float(row[1] or 0), cantidad=row[2])
        for row in r3.all()
    ]

    return VentasPeriodoResponse(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        total=_D(total),
        cantidad_documentos=cantidad or 0,
        por_cliente=por_cliente,
        por_marca=por_marca,
    )


# ══════════════════════════════════════════════════════════
# RETENCIONES ACUMULADAS
# ══════════════════════════════════════════════════════════

@router.get("/retenciones-periodo", response_model=RetencionesPeriodoResponse)
async def retenciones_periodo(
    _: CurrentUser,
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    fecha_desde, fecha_hasta = _default_rango(fecha_desde, fecha_hasta)

    rc = await db.execute(
        select(
            func.coalesce(func.sum(CompraDocumento.retefuente), 0),
            func.coalesce(func.sum(CompraDocumento.reteiva), 0),
            func.coalesce(func.sum(CompraDocumento.reteica), 0),
        ).where(
            CompraDocumento.fecha.between(fecha_desde, fecha_hasta),
            CompraDocumento.estado != "Anulada",
        )
    )
    c_rf, c_ri, c_rc = rc.one()

    rv = await db.execute(
        select(
            func.coalesce(func.sum(VentaDocumento.retefuente), 0),
            func.coalesce(func.sum(VentaDocumento.reteiva), 0),
            func.coalesce(func.sum(VentaDocumento.reteica), 0),
        ).where(
            VentaDocumento.fecha.between(fecha_desde, fecha_hasta),
            VentaDocumento.estado != EstadoVenta.ANULADA,
        )
    )
    v_rf, v_ri, v_rc = rv.one()

    return RetencionesPeriodoResponse(
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        compras_retefuente=_D(c_rf), compras_reteiva=_D(c_ri), compras_reteica=_D(c_rc),
        ventas_retefuente=_D(v_rf), ventas_reteiva=_D(v_ri), ventas_reteica=_D(v_rc),
        total_retefuente=_D(c_rf) + _D(v_rf),
        total_reteiva=_D(c_ri) + _D(v_ri),
        total_reteica=_D(c_rc) + _D(v_rc),
    )
