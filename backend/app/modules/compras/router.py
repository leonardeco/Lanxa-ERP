from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.numbering import next_sequential_numero
from app.api.deps import CurrentUser, AdminOrAdministradoraDep

from .models import Proveedor, CompraDocumento, CompraDetalle
from .schemas import (
    ProveedorCreate, ProveedorUpdate, ProveedorResponse,
    CompraInput, CompraResponse, ComprasDashboard, TopProveedor,
)
from app.modules.contabilidad.models import CuentaPorPagar, EstadoDocumento
from app.modules.inventario.models import TipoMovimientoInventario, OrigenMovimiento
from app.modules.inventario.service import registrar_movimiento

router = APIRouter(prefix="/api/v1/compras", tags=["Compras & Proveedores"])


# ══════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=ComprasDashboard)
async def get_dashboard(
    _: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    hoy = date.today()
    mes = hoy.month
    anio = hoy.year
    mes_ant = mes - 1 if mes > 1 else 12
    anio_ant = anio if mes > 1 else anio - 1

    r = await session.execute(
        select(func.sum(CompraDocumento.total), func.count(CompraDocumento.id))
        .where(
            extract("year", CompraDocumento.fecha) == anio,
            extract("month", CompraDocumento.fecha) == mes,
            CompraDocumento.estado != "Anulada",
        )
    )
    row = r.one()
    total_mes = row[0] or Decimal("0")
    cant_mes = row[1] or 0

    r2 = await session.execute(
        select(func.sum(CompraDocumento.total))
        .where(
            extract("year", CompraDocumento.fecha) == anio_ant,
            extract("month", CompraDocumento.fecha) == mes_ant,
            CompraDocumento.estado != "Anulada",
        )
    )
    total_mes_ant = r2.scalar() or Decimal("0")

    r3 = await session.execute(
        select(func.count(Proveedor.id)).where(Proveedor.activo == True)  # noqa: E712
    )
    prov_activos = r3.scalar() or 0

    r4 = await session.execute(
        select(func.sum(CompraDocumento.total))
        .where(
            CompraDocumento.estado_pago.in_(["Pendiente", "Parcial"]),
            CompraDocumento.estado != "Anulada",
        )
    )
    cxp_pend = r4.scalar() or Decimal("0")

    r5 = await session.execute(
        select(
            CompraDocumento.proveedor_razon_social,
            func.sum(CompraDocumento.total).label("total"),
        )
        .where(
            extract("year", CompraDocumento.fecha) == anio,
            extract("month", CompraDocumento.fecha) == mes,
            CompraDocumento.estado != "Anulada",
        )
        .group_by(CompraDocumento.proveedor_razon_social)
        .order_by(func.sum(CompraDocumento.total).desc())
        .limit(5)
    )
    top_prov = [TopProveedor(proveedor=row[0], total=float(row[1])) for row in r5.all()]

    return ComprasDashboard(
        total_compras_mes=total_mes,
        total_compras_mes_anterior=total_mes_ant,
        cantidad_compras_mes=cant_mes,
        total_proveedores_activos=prov_activos,
        cxp_pendiente=cxp_pend,
        top_proveedores=top_prov,
    )


# ══════════════════════════════════════════════════════════
# PROVEEDORES
# ══════════════════════════════════════════════════════════

@router.get("/proveedores", response_model=list[ProveedorResponse])
async def list_proveedores(
    _: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Proveedor).order_by(Proveedor.razon_social))
    return result.scalars().all()


@router.post("/proveedores", response_model=ProveedorResponse, status_code=201)
async def create_proveedor(
    data: ProveedorCreate,
    _: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    existing = await session.execute(select(Proveedor).where(Proveedor.nit_cc == data.nit_cc))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Ya existe un proveedor con NIT {data.nit_cc}")
    proveedor = Proveedor(**data.model_dump())
    session.add(proveedor)
    await session.commit()
    await session.refresh(proveedor)
    return proveedor


@router.put("/proveedores/{id}", response_model=ProveedorResponse)
async def update_proveedor(
    id: int,
    data: ProveedorUpdate,
    _: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Proveedor).where(Proveedor.id == id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(p, field, value)
    await session.commit()
    await session.refresh(p)
    return p


@router.delete("/proveedores/{id}", status_code=204)
async def delete_proveedor(
    id: int,
    _: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Proveedor).where(Proveedor.id == id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    p.activo = False
    await session.commit()


# ══════════════════════════════════════════════════════════
# DOCUMENTOS DE COMPRA
# ══════════════════════════════════════════════════════════

def _calc_lineas(detalles_input):
    subtotal = Decimal("0")
    desc_total = Decimal("0")
    iva_total = Decimal("0")
    lineas = []

    for d in detalles_input:
        cant = Decimal(str(d.cantidad))
        precio = Decimal(str(d.precio_unitario))
        desc_pct = Decimal(str(d.descuento_porcentaje))
        iva_pct = Decimal(str(d.iva_porcentaje))

        sub = (cant * precio).quantize(Decimal("0.01"))
        desc = (sub * desc_pct / 100).quantize(Decimal("0.01"))
        base = sub - desc
        iva = (base * iva_pct / 100).quantize(Decimal("0.01"))

        subtotal += sub
        desc_total += desc
        iva_total += iva

        lineas.append({
            "descripcion": d.descripcion,
            "producto_id": d.producto_id,
            "cantidad": cant,
            "precio_unitario": precio,
            "descuento_porcentaje": desc_pct,
            "iva_porcentaje": iva_pct,
            "subtotal_linea": base,
            "iva_valor": iva,
            "total_linea": base + iva,
        })

    return subtotal, desc_total, subtotal - desc_total, iva_total, lineas


@router.get("/", response_model=list[CompraResponse])
async def list_compras(
    _: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(CompraDocumento)
        .options(selectinload(CompraDocumento.detalles))
        .order_by(CompraDocumento.id.desc())
    )
    return result.scalars().all()


@router.get("/{id}", response_model=CompraResponse)
async def get_compra(
    id: int,
    _: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(CompraDocumento)
        .options(selectinload(CompraDocumento.detalles))
        .where(CompraDocumento.id == id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return c


@router.post("/", response_model=CompraResponse, status_code=201)
async def create_compra(
    data: CompraInput,
    _: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    if not data.detalles:
        raise HTTPException(status_code=400, detail="La compra debe tener al menos una línea de detalle")

    prov = (await session.execute(select(Proveedor).where(Proveedor.id == data.proveedor_id))).scalar_one_or_none()
    if not prov:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    # Auto-number robusto y basado en MAX del sufijo
    numero = await next_sequential_numero(session, CompraDocumento.numero, "SOG-CP")

    subtotal, desc_total, base_grav, iva_total, lineas = _calc_lineas(data.detalles)
    rete = Decimal(str(data.retefuente))
    reteiva = Decimal(str(data.reteiva))
    reteica = Decimal(str(data.reteica))
    total = base_grav + iva_total - rete - reteiva - reteica

    compra = CompraDocumento(
        numero=numero,
        fecha=data.fecha,
        fecha_vencimiento=data.fecha_vencimiento,
        proveedor_id=data.proveedor_id,
        proveedor_razon_social=prov.razon_social,
        proveedor_nit=prov.nit_cc,
        ref_proveedor=data.ref_proveedor,
        subtotal=subtotal,
        descuento_total=desc_total,
        base_gravable=base_grav,
        iva_total=iva_total,
        retefuente=rete,
        reteiva=reteiva,
        reteica=reteica,
        total=total,
        observaciones=data.observaciones,
    )
    session.add(compra)
    await session.flush()

    for linea in lineas:
        session.add(CompraDetalle(compra_id=compra.id, **linea))

    await session.commit()

    result = await session.execute(
        select(CompraDocumento)
        .options(selectinload(CompraDocumento.detalles))
        .where(CompraDocumento.id == compra.id)
    )
    return result.scalar_one()


@router.post("/{id}/confirmar", response_model=CompraResponse)
async def confirmar_compra(
    id: int,
    current: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(CompraDocumento).options(selectinload(CompraDocumento.detalles)).where(CompraDocumento.id == id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if c.estado != "Borrador":
        raise HTTPException(status_code=400, detail=f"No se puede confirmar: estado actual es '{c.estado}'")
    c.estado = "Confirmada"

    # Crear CxP automáticamente si no existe ya una para esta compra
    existing_cxp = await session.execute(
        select(CuentaPorPagar).where(CuentaPorPagar.numero_documento == c.numero)
    )
    if not existing_cxp.scalar_one_or_none():
        cxp = CuentaPorPagar(
            numero_documento=c.numero,
            fecha=c.fecha,
            fecha_vencimiento=c.fecha_vencimiento,
            proveedor_nit=c.proveedor_nit or "",
            razon_social=c.proveedor_razon_social,
            concepto=f"Compra {c.numero}" + (f" — Ref: {c.ref_proveedor}" if c.ref_proveedor else ""),
            valor=c.total,
            abonos=Decimal("0"),
            estado=EstadoDocumento.PENDIENTE,
            compra_id=c.id,
            notas=c.observaciones,
        )
        session.add(cxp)

    # Entradas automáticas de inventario por cada línea vinculada a un producto
    for d in c.detalles:
        if d.producto_id:
            await registrar_movimiento(
                session,
                producto_id=d.producto_id,
                tipo=TipoMovimientoInventario.ENTRADA,
                origen=OrigenMovimiento.COMPRA,
                cantidad=d.cantidad,
                motivo=f"Entrada por compra {c.numero}",
                usuario_id=current.id,
                compra_id=c.id,
                compra_detalle_id=d.id,
                costo_unitario=d.precio_unitario,
            )

    await session.commit()
    await session.refresh(c)
    return c


@router.post("/{id}/anular", response_model=CompraResponse)
async def anular_compra(
    id: int,
    current: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(CompraDocumento).options(selectinload(CompraDocumento.detalles)).where(CompraDocumento.id == id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    if c.estado == "Anulada":
        raise HTTPException(status_code=400, detail="La compra ya está anulada")

    estado_anterior = c.estado
    c.estado = "Anulada"
    c.estado_pago = "Anulado"

    # Si la compra ya había generado entradas de inventario, revertirlas
    if estado_anterior == "Confirmada":
        for d in c.detalles:
            if d.producto_id:
                await registrar_movimiento(
                    session,
                    producto_id=d.producto_id,
                    tipo=TipoMovimientoInventario.SALIDA,
                    origen=OrigenMovimiento.REVERSO_COMPRA,
                    cantidad=d.cantidad,
                    motivo=f"Reverso por anulación de compra {c.numero}",
                    usuario_id=current.id,
                    compra_id=c.id,
                    compra_detalle_id=d.id,
                )

    await session.commit()
    await session.refresh(c)
    return c
