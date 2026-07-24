"""
Super Ozono Global — API Routes (Ventas Diarias, Run 6)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from decimal import Decimal
from datetime import date

from app.core.database import get_db
from app.core.tenancy import for_tenant, get_for_tenant
from app.api.deps import ContableDep
from app.modules.ventas.models import Cliente, Producto
from app.modules.ventas_diarias.models import (
    VentaDiaria, VentaDiariaDetalle, PagoSuelto, EstadoVentaDiaria,
)
from app.modules.ventas_diarias.schemas import (
    VentaDiariaCreate, VentaDiariaResponse,
    VentaDiariaResumenMensual, PagoSueltoResponse, PagoSueltoUpdate,
)

router = APIRouter(prefix="/api/v1/ventas-diarias", tags=["Ventas Diarias"])

_EAGER = (selectinload(VentaDiaria.detalles),)


def _calcular_saldo(
    venta: Optional[Decimal], abono_1: Optional[Decimal], abono_2: Optional[Decimal]
) -> Decimal:
    v = venta or Decimal("0")
    a1 = abono_1 or Decimal("0")
    a2 = abono_2 or Decimal("0")
    return v - a1 - a2


async def _get_venta_diaria_or_404(db: AsyncSession, venta_diaria_id: int) -> VentaDiaria:
    venta = await db.scalar(
        for_tenant(
            select(VentaDiaria).options(*_EAGER).where(VentaDiaria.id == venta_diaria_id),
            VentaDiaria,
        )
    )
    if not venta:
        raise HTTPException(status_code=404, detail="Venta diaria no encontrada")
    return venta


@router.get("/", response_model=List[VentaDiariaResponse])
async def list_ventas_diarias(
    _: ContableDep,
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    estado: Optional[str] = Query(None),
    asesor: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Listar ventas diarias del tenant actual (paginado, mas recientes primero)."""
    query = for_tenant(
        select(VentaDiaria).options(*_EAGER)
        .order_by(desc(VentaDiaria.fecha), desc(VentaDiaria.id))
        .limit(limit).offset(offset),
        VentaDiaria,
    )
    if fecha_desde:
        query = query.where(VentaDiaria.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.where(VentaDiaria.fecha <= fecha_hasta)
    if estado:
        query = query.where(VentaDiaria.estado == estado)
    if asesor:
        query = query.where(VentaDiaria.asesor == asesor)
    rows = (await db.execute(query)).scalars().unique().all()
    return rows


@router.post("/", response_model=VentaDiariaResponse, status_code=201)
async def create_venta_diaria(
    data: VentaDiariaCreate, _: ContableDep, db: AsyncSession = Depends(get_db),
):
    """Crear una venta diaria con sus lineas de producto. El saldo de cada
    linea se calcula en el servidor (venta - abono_1 - abono_2), nunca se
    acepta del cliente."""
    cliente = await get_for_tenant(db, Cliente, data.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    venta = VentaDiaria(
        fecha=data.fecha,
        asesor=data.asesor,
        guia=data.guia,
        codigo_guia=data.codigo_guia,
        cliente_id=data.cliente_id,
        estado=data.estado,
        forma_pago=data.forma_pago,
        notas=data.notas,
    )
    db.add(venta)
    await db.flush()

    for linea in data.detalles:
        producto = await get_for_tenant(db, Producto, linea.producto_id)
        if not producto:
            raise HTTPException(
                status_code=404, detail=f"Producto {linea.producto_id} no encontrado")
        db.add(VentaDiariaDetalle(
            venta_diaria_id=venta.id,
            producto_id=linea.producto_id,
            cantidad=linea.cantidad,
            venta=linea.venta,
            abono_1=linea.abono_1,
            abono_2=linea.abono_2,
            saldo=_calcular_saldo(linea.venta, linea.abono_1, linea.abono_2),
            pesos_c=linea.pesos_c,
            valor_flete=linea.valor_flete,
        ))

    await db.flush()
    return await _get_venta_diaria_or_404(db, venta.id)


@router.get("/resumen/{anio}/{mes}", response_model=VentaDiariaResumenMensual)
async def resumen_mensual(
    anio: int, mes: int, _: ContableDep, db: AsyncSession = Depends(get_db),
):
    """Totales del mes para el tenant actual: venta, abonado, saldo pendiente
    y conteo de entregados/devoluciones."""
    totales_query = for_tenant(
        select(
            func.coalesce(func.sum(VentaDiariaDetalle.venta), 0),
            func.coalesce(
                func.sum(
                    func.coalesce(VentaDiariaDetalle.abono_1, 0)
                    + func.coalesce(VentaDiariaDetalle.abono_2, 0)
                ),
                0,
            ),
            func.coalesce(func.sum(VentaDiariaDetalle.saldo), 0),
        )
        .join(VentaDiaria, VentaDiaria.id == VentaDiariaDetalle.venta_diaria_id)
        .where(
            extract("year", VentaDiaria.fecha) == anio,
            extract("month", VentaDiaria.fecha) == mes,
        ),
        VentaDiariaDetalle,
    )
    total_venta, total_abonado, total_saldo = (await db.execute(totales_query)).one()

    conteo_query = for_tenant(
        select(VentaDiaria.estado, func.count(VentaDiaria.id))
        .where(
            extract("year", VentaDiaria.fecha) == anio,
            extract("month", VentaDiaria.fecha) == mes,
        )
        .group_by(VentaDiaria.estado),
        VentaDiaria,
    )
    conteos = dict((await db.execute(conteo_query)).all())

    return VentaDiariaResumenMensual(
        anio=anio,
        mes=mes,
        total_venta=total_venta,
        total_abonado=total_abonado,
        total_saldo=total_saldo,
        cantidad_entregado=conteos.get(EstadoVentaDiaria.ENTREGADO, 0),
        cantidad_devolucion=conteos.get(EstadoVentaDiaria.DEVOLUCION, 0),
    )


@router.get("/pagos-sueltos/", response_model=List[PagoSueltoResponse])
async def list_pagos_sueltos(
    _: ContableDep,
    revisado: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = for_tenant(
        select(PagoSuelto).order_by(desc(PagoSuelto.fecha)), PagoSuelto)
    if revisado is not None:
        query = query.where(PagoSuelto.revisado == revisado)
    rows = (await db.execute(query)).scalars().all()
    return rows


@router.patch("/pagos-sueltos/{pago_id}", response_model=PagoSueltoResponse)
async def marcar_pago_suelto(
    pago_id: int, data: PagoSueltoUpdate, _: ContableDep,
    db: AsyncSession = Depends(get_db),
):
    pago = await get_for_tenant(db, PagoSuelto, pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago suelto no encontrado")
    pago.revisado = data.revisado
    await db.flush()
    return pago


@router.get("/{venta_diaria_id}", response_model=VentaDiariaResponse)
async def get_venta_diaria(
    venta_diaria_id: int, _: ContableDep, db: AsyncSession = Depends(get_db),
):
    return await _get_venta_diaria_or_404(db, venta_diaria_id)
