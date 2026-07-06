from decimal import Decimal
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.numbering import next_sequential_numero
from app.api.deps import CurrentUser, AdminOrAdministradoraDep

from .models import (
    Proveedor, CompraDocumento, CompraDetalle,
    DevolucionCompra, DevolucionCompraDetalle,
)
from app.modules.ventas.models import Producto
from .schemas import (
    ProveedorCreate, ProveedorUpdate, ProveedorResponse,
    CompraInput, CompraResponse, ComprasDashboard, TopProveedor,
    DevolucionCompraCreate, DevolucionCompraResponse,
)
from app.modules.contabilidad.models import CuentaPorPagar, EstadoDocumento
from app.modules.contabilidad.asientos import (
    asiento_compra_confirmada, asiento_devolucion_compra, reversar_asientos,
)
from app.modules.inventario.models import TipoMovimientoInventario, OrigenMovimiento
from app.modules.inventario.service import registrar_movimiento
from app.modules.auditoria.service import registrar_auditoria, diff_cambios

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
    current: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    existing = await session.execute(select(Proveedor).where(Proveedor.nit_cc == data.nit_cc))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Ya existe un proveedor con NIT {data.nit_cc}")
    proveedor = Proveedor(**data.model_dump())
    session.add(proveedor)
    await session.flush()
    registrar_auditoria(session, current, "Crear", "Proveedor", proveedor.id,
                        f"Proveedor {proveedor.nit_cc} — {proveedor.razon_social}")
    await session.commit()
    await session.refresh(proveedor)
    return proveedor


@router.put("/proveedores/{id}", response_model=ProveedorResponse)
async def update_proveedor(
    id: int,
    data: ProveedorUpdate,
    current: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Proveedor).where(Proveedor.id == id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    update_data = data.model_dump(exclude_none=True)
    cambios = diff_cambios(p, update_data)
    for field, value in update_data.items():
        setattr(p, field, value)
    if cambios:
        registrar_auditoria(session, current, "Actualizar", "Proveedor", p.id,
                            f"Proveedor {p.nit_cc} — {p.razon_social}", cambios)
    await session.commit()
    await session.refresh(p)
    return p


@router.delete("/proveedores/{id}", status_code=204)
async def delete_proveedor(
    id: int,
    current: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(Proveedor).where(Proveedor.id == id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    p.activo = False
    registrar_auditoria(session, current, "Desactivar", "Proveedor", p.id,
                        f"Proveedor {p.nit_cc} — {p.razon_social}")
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
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    """Listar compras (paginado: limit/offset, más recientes primero)."""
    result = await session.execute(
        select(CompraDocumento)
        .options(selectinload(CompraDocumento.detalles))
        .order_by(CompraDocumento.id.desc())
        .limit(limit)
        .offset(offset)
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

    # Asiento contable automático (partida doble)
    await asiento_compra_confirmada(session, c, usuario_id=current.id)

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

    # BUG-007 (espejo de ventas): con devoluciones a proveedor no se puede
    # anular — el reverso duplicaría la salida de stock ya hecha por la ND.
    tiene_nd = await session.scalar(
        select(DevolucionCompra.id).where(DevolucionCompra.compra_id == c.id).limit(1)
    )
    if tiene_nd:
        raise HTTPException(
            status_code=400,
            detail="La compra tiene devoluciones a proveedor asociadas y no se "
                   "puede anular. El saldo ya fue ajustado por las devoluciones.",
        )

    # BUG-008 (espejo): si la CxP ya tiene abonos, primero se anulan los pagos
    cxp = await session.scalar(
        select(CuentaPorPagar).where(CuentaPorPagar.numero_documento == c.numero)
    )
    if cxp and (cxp.abonos or Decimal("0")) > 0:
        raise HTTPException(
            status_code=400,
            detail="La compra tiene pagos registrados. Anula primero los pagos "
                   "en Cartera y vuelve a intentar.",
        )

    estado_anterior = c.estado
    c.estado = "Anulada"
    c.estado_pago = "Anulado"

    # La CxP generada al confirmar también se anula (antes quedaba viva
    # mostrando un pago pendiente de una compra anulada)
    if cxp and cxp.estado != EstadoDocumento.ANULADO:
        cxp.estado = EstadoDocumento.ANULADO
        cxp.notas = ((cxp.notas or "") + f"\n[ANULADA] junto con la compra {c.numero}").strip()

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

    # Reverso del asiento contable si la compra ya lo había generado
    await reversar_asientos(
        session, documento_ref=c.numero, usuario_id=current.id,
        motivo=f"Anulación de compra {c.numero}",
    )

    await session.commit()
    await session.refresh(c)
    return c


# ══════════════════════════════════════════════════════════
# DEVOLUCIONES A PROVEEDOR (ND-####)
# ══════════════════════════════════════════════════════════

@router.get("/{id}/devoluciones", response_model=list[DevolucionCompraResponse])
async def list_devoluciones_compra(id: int, _: CurrentUser, session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(
        select(DevolucionCompra)
        .options(selectinload(DevolucionCompra.detalles))
        .where(DevolucionCompra.compra_id == id)
        .order_by(DevolucionCompra.id)
    )).scalars().all()
    return rows


@router.post("/{id}/devoluciones", response_model=DevolucionCompraResponse, status_code=201)
async def crear_devolucion_compra(
    id: int,
    data: DevolucionCompraCreate,
    current: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    """
    Devolución a proveedor sobre una compra confirmada: saca la mercancía del
    inventario (valida stock), reduce la CxP y genera el asiento contable
    (DB 220501 Proveedores / CR 143501 Inventario + 240802 IVA descontable).
    """
    compra = await session.scalar(
        select(CompraDocumento)
        .options(selectinload(CompraDocumento.detalles))
        .where(CompraDocumento.id == id)
    )
    if not compra:
        raise HTTPException(404, "Compra no encontrada")
    if compra.estado != "Confirmada":
        raise HTTPException(400, "Solo se pueden devolver compras Confirmadas")

    detalles_compra = {d.id: d for d in compra.detalles}

    ya_devueltas: dict[int, Decimal] = {}
    previas = (await session.execute(
        select(DevolucionCompraDetalle.compra_detalle_id, func.sum(DevolucionCompraDetalle.cantidad))
        .join(DevolucionCompra, DevolucionCompra.id == DevolucionCompraDetalle.devolucion_id)
        .where(DevolucionCompra.compra_id == id)
        .group_by(DevolucionCompraDetalle.compra_detalle_id)
    )).all()
    for det_id, cant in previas:
        ya_devueltas[det_id] = Decimal(str(cant))

    numero = await next_sequential_numero(session, DevolucionCompra.numero, "ND")
    devolucion = DevolucionCompra(
        numero=numero,
        compra_id=compra.id,
        fecha=data.fecha or date.today(),
        motivo=data.motivo,
        usuario_id=current.id,
    )
    session.add(devolucion)
    await session.flush()

    subtotal = Decimal("0.00")
    iva_total = Decimal("0.00")
    for item in data.detalles:
        det = detalles_compra.get(item.compra_detalle_id)
        if not det:
            raise HTTPException(404, f"La línea {item.compra_detalle_id} no pertenece a esta compra")
        disponible = det.cantidad - ya_devueltas.get(det.id, Decimal("0"))
        if item.cantidad > disponible:
            raise HTTPException(
                400,
                f"No se puede devolver {item.cantidad} de la línea {det.id}: "
                f"compradas {det.cantidad}, ya devueltas {ya_devueltas.get(det.id, 0)} "
                f"(máximo {disponible})",
            )

        base = (item.cantidad * det.precio_unitario
                * (Decimal("1") - det.descuento_porcentaje / Decimal("100")))
        base = base.quantize(Decimal("0.01"))
        iva = (base * det.iva_porcentaje / Decimal("100")).quantize(Decimal("0.01"))
        subtotal += base
        iva_total += iva

        session.add(DevolucionCompraDetalle(
            devolucion_id=devolucion.id,
            compra_detalle_id=det.id,
            producto_id=det.producto_id,
            descripcion=det.descripcion,
            cantidad=item.cantidad,
            precio_unitario=det.precio_unitario,
            subtotal_linea=base,
            iva_valor=iva,
            total_linea=base + iva,
        ))

        # La mercancía devuelta sale del inventario (si la línea tiene producto)
        if det.producto_id:
            producto = await session.get(Producto, det.producto_id)
            stock = producto.stock_actual if producto else Decimal("0")
            if stock < item.cantidad:
                nombre = producto.nombre if producto else det.descripcion
                raise HTTPException(
                    400,
                    f"Stock insuficiente para devolver {item.cantidad} de "
                    f"{nombre} (disponible: {stock})",
                )
            await registrar_movimiento(
                session,
                producto_id=det.producto_id,
                tipo=TipoMovimientoInventario.SALIDA,
                origen=OrigenMovimiento.DEVOLUCION_COMPRA,
                cantidad=item.cantidad,
                motivo=f"Devolución {numero} de compra {compra.numero}: {data.motivo}",
                usuario_id=current.id,
                compra_id=compra.id,
                compra_detalle_id=det.id,
            )

    devolucion.subtotal = subtotal
    devolucion.iva_total = iva_total
    devolucion.total = subtotal + iva_total

    # Reducir la CxP de la compra. Si ya se había pagado más de lo que queda,
    # la CxP pasa a Pagado y el saldo a favor se gestiona manualmente.
    cxp = await session.scalar(
        select(CuentaPorPagar).where(CuentaPorPagar.compra_id == compra.id)
    )
    if cxp and cxp.estado != EstadoDocumento.ANULADO:
        cxp.valor = max(cxp.valor - devolucion.total, Decimal("0"))
        saldo = cxp.valor - (cxp.abonos or Decimal("0"))
        if saldo <= 0:
            cxp.estado = EstadoDocumento.PAGADO
            compra.estado_pago = "Pagado"
        elif (cxp.abonos or Decimal("0")) > 0:
            cxp.estado = EstadoDocumento.PARCIAL
        else:
            cxp.estado = EstadoDocumento.PENDIENTE
        nota_nd = f"[ND] {numero}: -{devolucion.total}"
        cxp.notas = ((cxp.notas or "") + "\n" + nota_nd).strip()

    # Asiento contable (valida período abierto)
    await asiento_devolucion_compra(session, devolucion, compra, usuario_id=current.id)

    await session.commit()

    result = await session.scalar(
        select(DevolucionCompra)
        .options(selectinload(DevolucionCompra.detalles))
        .where(DevolucionCompra.id == devolucion.id)
    )
    return result
