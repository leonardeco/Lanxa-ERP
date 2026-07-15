"""
Super Ozono Global — API Routes (Ventas & Comercial)
CRUD completo para Productos, Clientes y Documentos de Venta
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, desc, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from decimal import Decimal
from datetime import date, timedelta

from app.core.database import get_db
from app.core.config import get_settings
from app.core.numbering import next_sequential_numero
from app.core.tenancy import for_tenant, get_for_tenant, tenant_clause
from app.api.deps import CurrentUser, AdminOrAdministradoraDep
from app.modules.ventas.models import (
    Producto, Cliente, VentaDocumento, VentaDetalle,
    Cotizacion, CotizacionDetalle, EstadoCotizacion,
    DevolucionVenta, DevolucionVentaDetalle,
    EstadoVenta, EstadoPago,
)
from app.modules.ventas.schemas import (
    ProductoCreate, ProductoUpdate, ProductoResponse,
    ClienteCreate, ClienteUpdate, ClienteResponse,
    VentaCreate, VentaResponse, VentaDetalleCreate, VentaDetalleResponse,
    CotizacionCreate, CotizacionRechazo, CotizacionResponse,
    VentaDashboardStats,
    DevolucionCreate, DevolucionResponse,
)
from app.modules.inventario.models import TipoMovimientoInventario, OrigenMovimiento
from app.modules.inventario.service import registrar_movimiento
from app.modules.inventario.lotes import revertir_por_lotes
from app.modules.contabilidad.models import CuentaPorCobrar, EstadoDocumento, ParametroTributario
from app.modules.ventas import services as ventas_service
from app.modules.contabilidad.asientos import asiento_devolucion_venta
from app.modules.auditoria.service import registrar_auditoria, diff_cambios

router = APIRouter(prefix="/api/v1/ventas", tags=["Ventas & Comercial"])
settings = get_settings()

# Conceptos de ParametroTributario usados para sugerir retenciones en ventas
_CONCEPTO_RETEFUENTE = "Retención en la fuente - compras"
_CONCEPTO_RETEIVA = "ReteIVA"


async def _sugerir_retenciones(db: AsyncSession, cliente, base_gravable: Decimal, iva_total: Decimal):
    """Sugiere (retefuente, reteiva, reteica) según el perfil tributario del cliente
    y las tarifas vigentes en ParametroTributario. Es solo una sugerencia: el
    endpoint permite override manual por factura."""
    rows = (await db.execute(
        select(ParametroTributario).where(
            ParametroTributario.concepto.in_([_CONCEPTO_RETEFUENTE, _CONCEPTO_RETEIVA]),
            ParametroTributario.activo == True,  # noqa: E712
        )
    )).scalars().all()
    rates = {r.concepto: (r.tarifa_valor or Decimal("0")) for r in rows}

    retefuente = Decimal("0.00")
    reteiva = Decimal("0.00")
    reteica = Decimal("0.00")

    if getattr(cliente, "retiene_fuente", False):
        umbral = settings.RETEFUENTE_BASE_UVT * settings.UVT_VALOR
        if base_gravable >= umbral:
            retefuente = round(base_gravable * rates.get(_CONCEPTO_RETEFUENTE, Decimal("0")), 2)
    if getattr(cliente, "retiene_iva", False):
        reteiva = round(iva_total * rates.get(_CONCEPTO_RETEIVA, Decimal("0")), 2)
    if getattr(cliente, "retiene_ica", False) and cliente.tarifa_reteica:
        reteica = round(base_gravable * (cliente.tarifa_reteica / Decimal("1000")), 2)

    return retefuente, reteiva, reteica


# ══════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════

async def _next_venta_numero(db: AsyncSession) -> str:
    """Genera el siguiente número de venta: SOG-V-0001, SOG-V-0002..."""
    return await next_sequential_numero(db, VentaDocumento.numero, "SOG-V")


def _calcular_detalle(detalle_data) -> dict:
    """Calcula los valores de una línea de venta."""
    cantidad = detalle_data.cantidad
    precio = detalle_data.precio_unitario
    descuento_pct = detalle_data.descuento_porcentaje
    iva_pct = detalle_data.iva_porcentaje

    subtotal = cantidad * precio
    descuento_valor = subtotal * (descuento_pct / Decimal("100"))
    base = subtotal - descuento_valor
    iva_valor = base * (iva_pct / Decimal("100"))
    total = base + iva_valor

    return {
        "subtotal_linea": round(base, 2),
        "iva_valor": round(iva_valor, 2),
        "total_linea": round(total, 2),
    }


def _build_venta_response(venta: VentaDocumento) -> VentaResponse:
    """Construye el VentaResponse. Requiere que venta.cliente y venta.detalles
    (con .producto) estén precargados vía selectinload — sin queries extra."""
    detalles_resp = [
        VentaDetalleResponse(
            id=d.id,
            producto_id=d.producto_id,
            cantidad=d.cantidad,
            precio_unitario=d.precio_unitario,
            descuento_porcentaje=d.descuento_porcentaje,
            subtotal_linea=d.subtotal_linea,
            iva_porcentaje=d.iva_porcentaje,
            iva_valor=d.iva_valor,
            total_linea=d.total_linea,
            notas=d.notas,
            created_at=d.created_at,
            producto_nombre=d.producto.nombre if d.producto else None,
            producto_sku=d.producto.sku if d.producto else None,
        )
        for d in venta.detalles
    ]
    cliente = venta.cliente
    return VentaResponse(
        id=venta.id,
        numero=venta.numero,
        fecha=venta.fecha,
        fecha_vencimiento=venta.fecha_vencimiento,
        cliente_id=venta.cliente_id,
        centro_costo_id=venta.centro_costo_id,
        vendedor=venta.vendedor,
        subtotal=venta.subtotal,
        descuento_total=venta.descuento_total,
        base_gravable=venta.base_gravable,
        iva_total=venta.iva_total,
        retefuente=venta.retefuente,
        reteiva=venta.reteiva,
        reteica=venta.reteica,
        total=venta.total,
        estado=venta.estado.value,
        estado_pago=venta.estado_pago.value,
        observaciones=venta.observaciones,
        created_at=venta.created_at,
        updated_at=venta.updated_at,
        cliente_razon_social=cliente.razon_social if cliente else None,
        cliente_nit=cliente.nit_cc if cliente else None,
        detalles=detalles_resp,
    )


_VENTA_EAGER = (
    selectinload(VentaDocumento.cliente),
    selectinload(VentaDocumento.detalles).selectinload(VentaDetalle.producto),
)


# ══════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=VentaDashboardStats)
async def get_ventas_dashboard(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Estadísticas del módulo de ventas."""
    hoy = date.today()
    mes_actual = hoy.month
    anio_actual = hoy.year

    # Ventas del mes actual
    ventas_mes = await db.scalar(
        select(func.coalesce(func.sum(VentaDocumento.total), 0))
        .where(
            extract("month", VentaDocumento.fecha) == mes_actual,
            extract("year", VentaDocumento.fecha) == anio_actual,
            VentaDocumento.estado != EstadoVenta.ANULADA,
        )
    )

    # Ventas del mes anterior
    mes_anterior = mes_actual - 1 if mes_actual > 1 else 12
    anio_anterior = anio_actual if mes_actual > 1 else anio_actual - 1
    ventas_mes_ant = await db.scalar(
        select(func.coalesce(func.sum(VentaDocumento.total), 0))
        .where(
            extract("month", VentaDocumento.fecha) == mes_anterior,
            extract("year", VentaDocumento.fecha) == anio_anterior,
            VentaDocumento.estado != EstadoVenta.ANULADA,
        )
    )

    # Cantidad de ventas del mes
    cant_ventas = await db.scalar(
        select(func.count(VentaDocumento.id))
        .where(
            extract("month", VentaDocumento.fecha) == mes_actual,
            extract("year", VentaDocumento.fecha) == anio_actual,
            VentaDocumento.estado != EstadoVenta.ANULADA,
        )
    )

    # Clientes y productos activos
    clientes_activos = await db.scalar(
        select(func.count(Cliente.id)).where(Cliente.activo == True)  # noqa: E712
    )
    productos_activos = await db.scalar(
        select(func.count(Producto.id)).where(Producto.activo == True)  # noqa: E712
    )

    # Productos con stock bajo
    stock_bajo = await db.scalar(
        select(func.count(Producto.id))
        .where(Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo)  # noqa: E712
    )

    # Ticket promedio
    ticket_prom = Decimal("0.00")
    if cant_ventas and cant_ventas > 0:
        ticket_prom = round(Decimal(str(ventas_mes)) / cant_ventas, 2)

    # Ventas por marca (top 10)
    result = await db.execute(
        select(
            Producto.marca,
            func.coalesce(func.sum(VentaDetalle.total_linea), 0).label("total"),
        )
        .join(VentaDetalle, VentaDetalle.producto_id == Producto.id, isouter=True)
        .join(
            VentaDocumento,
            and_(
                VentaDocumento.id == VentaDetalle.venta_id,
                VentaDocumento.estado != EstadoVenta.ANULADA,
            ),
            isouter=True,
        )
        .where(Producto.activo == True)  # noqa: E712
        .group_by(Producto.marca)
        .order_by(desc("total"))
        .limit(10)
    )
    ventas_marca = [
        {"marca": row[0], "total": float(row[1])} for row in result.all()
    ]

    return VentaDashboardStats(
        ventas_mes_actual=Decimal(str(ventas_mes or 0)),
        ventas_mes_anterior=Decimal(str(ventas_mes_ant or 0)),
        cantidad_ventas_mes=cant_ventas or 0,
        total_clientes_activos=clientes_activos or 0,
        total_productos_activos=productos_activos or 0,
        ticket_promedio=ticket_prom,
        productos_stock_bajo=stock_bajo or 0,
        ventas_por_marca=ventas_marca,
    )


# ══════════════════════════════════════════════════════════
# PRODUCTOS — CRUD
# ══════════════════════════════════════════════════════════

@router.get("/productos", response_model=List[ProductoResponse])
async def list_productos(
    _: CurrentUser,
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Listar productos con filtros opcionales (paginado: limit/offset)."""
    query = for_tenant(
        select(Producto).order_by(Producto.marca, Producto.nombre).limit(limit).offset(offset),
        Producto,
    )
    if marca:
        query = query.where(Producto.marca == marca)
    if activo is not None:
        query = query.where(Producto.activo == activo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
async def get_producto(producto_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Obtener un producto por ID."""
    producto = await get_for_tenant(db, Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("/productos", response_model=ProductoResponse, status_code=201)
async def create_producto(data: ProductoCreate, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Crear un nuevo producto."""
    # Verificar SKU único dentro del tenant
    existing = await db.scalar(
        select(Producto.id).where(Producto.sku == data.sku, tenant_clause(Producto))
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un producto con SKU '{data.sku}'")

    producto = Producto(**data.model_dump())
    db.add(producto)
    await db.flush()
    await db.refresh(producto)
    registrar_auditoria(db, current, "Crear", "Producto", producto.id,
                        f"Producto {producto.sku} — {producto.nombre}")
    await db.flush()
    return producto


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
async def update_producto(
    producto_id: int, data: ProductoUpdate, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)
):
    """Actualizar un producto existente."""
    producto = await get_for_tenant(db, Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    cambios = diff_cambios(producto, update_data)
    for field, value in update_data.items():
        setattr(producto, field, value)

    if cambios:
        registrar_auditoria(db, current, "Actualizar", "Producto", producto.id,
                            f"Producto {producto.sku} — {producto.nombre}", cambios)
    await db.flush()
    await db.refresh(producto)
    return producto


@router.delete("/productos/{producto_id}")
async def delete_producto(producto_id: int, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Desactivar un producto (soft delete)."""
    producto = await db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.activo = False
    registrar_auditoria(db, current, "Desactivar", "Producto", producto.id,
                        f"Producto {producto.sku} — {producto.nombre}")
    await db.flush()
    return {"detail": f"Producto '{producto.nombre}' desactivado correctamente"}


# ══════════════════════════════════════════════════════════
# CLIENTES — CRUD
# ══════════════════════════════════════════════════════════

@router.get("/clientes", response_model=List[ClienteResponse])
async def list_clientes(
    _: CurrentUser,
    activo: Optional[bool] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Listar clientes comerciales (paginado: limit/offset)."""
    query = for_tenant(
        select(Cliente).order_by(Cliente.razon_social).limit(limit).offset(offset),
        Cliente,
    )
    if activo is not None:
        query = query.where(Cliente.activo == activo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
async def get_cliente(cliente_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Obtener un cliente por ID."""
    cliente = await get_for_tenant(db, Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.post("/clientes", response_model=ClienteResponse, status_code=201)
async def create_cliente(data: ClienteCreate, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Crear un nuevo cliente."""
    existing = await db.scalar(
        select(Cliente.id).where(Cliente.nit_cc == data.nit_cc, tenant_clause(Cliente))
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un cliente con NIT/CC '{data.nit_cc}'")

    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    await db.flush()
    await db.refresh(cliente)
    registrar_auditoria(db, current, "Crear", "Cliente", cliente.id,
                        f"Cliente {cliente.nit_cc} — {cliente.razon_social}")
    await db.flush()
    return cliente


@router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
async def update_cliente(
    cliente_id: int, data: ClienteUpdate, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)
):
    """Actualizar un cliente existente."""
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    cambios = diff_cambios(cliente, update_data)
    for field, value in update_data.items():
        setattr(cliente, field, value)

    if cambios:
        registrar_auditoria(db, current, "Actualizar", "Cliente", cliente.id,
                            f"Cliente {cliente.nit_cc} — {cliente.razon_social}", cambios)
    await db.flush()
    await db.refresh(cliente)
    return cliente


@router.delete("/clientes/{cliente_id}")
async def delete_cliente(cliente_id: int, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Desactivar un cliente (soft delete)."""
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cliente.activo = False
    registrar_auditoria(db, current, "Desactivar", "Cliente", cliente.id,
                        f"Cliente {cliente.nit_cc} — {cliente.razon_social}")
    await db.flush()
    return {"detail": f"Cliente '{cliente.razon_social}' desactivado correctamente"}


# ══════════════════════════════════════════════════════════
# COTIZACIONES — COT-####
# (declaradas antes de las rutas /{venta_id} para que la ruta
#  literal /cotizaciones no sea capturada por el path param)
# ══════════════════════════════════════════════════════════

_COTIZACION_EAGER = (
    selectinload(Cotizacion.cliente),
    selectinload(Cotizacion.venta),
    selectinload(Cotizacion.detalles).selectinload(CotizacionDetalle.producto),
)


async def _aplicar_detalles_y_totales(
    db: AsyncSession, cot: Cotizacion, data: CotizacionCreate
) -> None:
    """Crea los detalles de la cotización (validando cada producto) y recalcula
    sus totales. `cot` ya debe estar en la sesión con su id (flush hecho). Al
    editar, los detalles previos deben haberse borrado antes de llamar aquí."""
    subtotal_total = Decimal("0.00")
    descuento_total = Decimal("0.00")
    iva_total = Decimal("0.00")
    for det_data in data.detalles:
        producto = await db.get(Producto, det_data.producto_id)
        if not producto:
            raise HTTPException(
                status_code=404, detail=f"Producto ID {det_data.producto_id} no encontrado")

        calc = _calcular_detalle(det_data)
        db.add(CotizacionDetalle(
            cotizacion_id=cot.id,
            producto_id=det_data.producto_id,
            cantidad=det_data.cantidad,
            precio_unitario=det_data.precio_unitario,
            descuento_porcentaje=det_data.descuento_porcentaje,
            subtotal_linea=calc["subtotal_linea"],
            iva_porcentaje=det_data.iva_porcentaje,
            iva_valor=calc["iva_valor"],
            total_linea=calc["total_linea"],
            notas=det_data.notas,
        ))
        linea_bruta = det_data.cantidad * det_data.precio_unitario
        subtotal_total += linea_bruta
        descuento_total += linea_bruta * (det_data.descuento_porcentaje / Decimal("100"))
        iva_total += calc["iva_valor"]

    base_gravable = subtotal_total - descuento_total
    cot.subtotal = round(subtotal_total, 2)
    cot.descuento_total = round(descuento_total, 2)
    cot.base_gravable = round(base_gravable, 2)
    cot.iva_total = round(iva_total, 2)
    cot.total = round(base_gravable + iva_total, 2)


def _build_cotizacion_response(cot: Cotizacion) -> CotizacionResponse:
    """Requiere cliente, venta y detalles (con .producto) precargados."""
    estado = cot.estado.value if hasattr(cot.estado, "value") else cot.estado
    vencida = (
        cot.estado in (EstadoCotizacion.BORRADOR, EstadoCotizacion.ENVIADA)
        and cot.fecha_vencimiento < date.today()
    )
    return CotizacionResponse(
        id=cot.id,
        numero=cot.numero,
        fecha=cot.fecha,
        vigencia_dias=cot.vigencia_dias,
        fecha_vencimiento=cot.fecha_vencimiento,
        cliente_id=cot.cliente_id,
        vendedor=cot.vendedor,
        subtotal=cot.subtotal,
        descuento_total=cot.descuento_total,
        base_gravable=cot.base_gravable,
        iva_total=cot.iva_total,
        total=cot.total,
        estado=estado,
        motivo_rechazo=cot.motivo_rechazo,
        venta_id=cot.venta_id,
        venta_numero=cot.venta.numero if cot.venta else None,
        vencida=vencida,
        observaciones=cot.observaciones,
        created_at=cot.created_at,
        updated_at=cot.updated_at,
        cliente_razon_social=cot.cliente.razon_social if cot.cliente else None,
        cliente_nit=cot.cliente.nit_cc if cot.cliente else None,
        detalles=[
            VentaDetalleResponse(
                id=d.id,
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
                descuento_porcentaje=d.descuento_porcentaje,
                subtotal_linea=d.subtotal_linea,
                iva_porcentaje=d.iva_porcentaje,
                iva_valor=d.iva_valor,
                total_linea=d.total_linea,
                notas=d.notas,
                producto_nombre=d.producto.nombre if d.producto else None,
                producto_sku=d.producto.sku if d.producto else None,
            )
            for d in cot.detalles
        ],
    )


async def _get_cotizacion_or_404(db: AsyncSession, cotizacion_id: int) -> Cotizacion:
    cot = await db.scalar(
        select(Cotizacion).options(*_COTIZACION_EAGER).where(Cotizacion.id == cotizacion_id)
    )
    if not cot:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return cot


@router.get("/cotizaciones", response_model=List[CotizacionResponse])
async def list_cotizaciones(
    _: CurrentUser,
    estado: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Listar cotizaciones (paginado, más recientes primero)."""
    query = (
        select(Cotizacion)
        .options(*_COTIZACION_EAGER)
        .order_by(desc(Cotizacion.fecha), desc(Cotizacion.id))
        .limit(limit)
        .offset(offset)
    )
    if estado:
        query = query.where(Cotizacion.estado == estado)
    rows = (await db.execute(query)).scalars().all()
    return [_build_cotizacion_response(c) for c in rows]


@router.get("/cotizaciones/{cotizacion_id}", response_model=CotizacionResponse)
async def get_cotizacion(cotizacion_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    return _build_cotizacion_response(await _get_cotizacion_or_404(db, cotizacion_id))


@router.post("/cotizaciones", response_model=CotizacionResponse, status_code=201)
async def create_cotizacion(
    data: CotizacionCreate, current: CurrentUser, db: AsyncSession = Depends(get_db)
):
    """Crear una cotización en Borrador. No toca inventario ni contabilidad."""
    cliente = await db.get(Cliente, data.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    numero = await next_sequential_numero(db, Cotizacion.numero, "COT")
    cot = Cotizacion(
        numero=numero,
        fecha=data.fecha,
        vigencia_dias=data.vigencia_dias,
        fecha_vencimiento=data.fecha + timedelta(days=data.vigencia_dias),
        cliente_id=data.cliente_id,
        vendedor=data.vendedor,
        observaciones=data.observaciones,
        estado=EstadoCotizacion.BORRADOR,
        usuario_id=current.id,
    )
    db.add(cot)
    await db.flush()

    await _aplicar_detalles_y_totales(db, cot, data)

    await db.flush()
    return _build_cotizacion_response(await _get_cotizacion_or_404(db, cot.id))


@router.put("/cotizaciones/{cotizacion_id}", response_model=CotizacionResponse)
async def update_cotizacion(
    cotizacion_id: int, data: CotizacionCreate, current: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Editar una cotización en Borrador: reemplaza cabecera y detalles y
    recalcula totales. Solo Borrador (409 en cualquier otro estado)."""
    cot = await _get_cotizacion_or_404(db, cotizacion_id)
    if cot.estado != EstadoCotizacion.BORRADOR:
        raise HTTPException(
            status_code=409, detail="Solo se pueden editar cotizaciones en Borrador")

    cliente = await db.get(Cliente, data.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cot.fecha = data.fecha
    cot.vigencia_dias = data.vigencia_dias
    cot.fecha_vencimiento = data.fecha + timedelta(days=data.vigencia_dias)
    cot.cliente_id = data.cliente_id
    cot.vendedor = data.vendedor
    cot.observaciones = data.observaciones

    # Reemplazar los detalles: borrar los viejos explícitamente, luego recrear.
    for det in list(cot.detalles):
        await db.delete(det)
    await db.flush()

    await _aplicar_detalles_y_totales(db, cot, data)

    registrar_auditoria(
        db, current, "Actualizar", "Cotizacion", cot.id,
        f"Editó la cotización {cot.numero} (total {cot.total})",
    )
    await db.flush()
    db.expire(cot, ["detalles"])
    return _build_cotizacion_response(await _get_cotizacion_or_404(db, cot.id))


@router.delete("/cotizaciones/{cotizacion_id}", status_code=204)
async def delete_cotizacion(
    cotizacion_id: int, current: CurrentUser, db: AsyncSession = Depends(get_db),
):
    """Eliminar una cotización en Borrador (borrado real; cascade borra los
    detalles). Deja rastro en auditoría. Solo Borrador (409 en otro estado)."""
    cot = await _get_cotizacion_or_404(db, cotizacion_id)
    if cot.estado != EstadoCotizacion.BORRADOR:
        raise HTTPException(
            status_code=409, detail="Solo se pueden eliminar cotizaciones en Borrador")

    registrar_auditoria(
        db, current, "Eliminar", "Cotizacion", cot.id,
        f"Eliminó la cotización {cot.numero} "
        f"(cliente {cot.cliente_id}, total {cot.total})",
    )
    await db.delete(cot)
    await db.flush()


@router.post("/cotizaciones/{cotizacion_id}/enviar", response_model=CotizacionResponse)
async def enviar_cotizacion(cotizacion_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Marcar la cotización como Enviada al cliente."""
    cot = await _get_cotizacion_or_404(db, cotizacion_id)
    if cot.estado != EstadoCotizacion.BORRADOR:
        raise HTTPException(status_code=400, detail="Solo se pueden enviar cotizaciones en Borrador")
    cot.estado = EstadoCotizacion.ENVIADA
    await db.flush()
    return _build_cotizacion_response(cot)


@router.post("/cotizaciones/{cotizacion_id}/aprobar", response_model=CotizacionResponse)
async def aprobar_cotizacion(cotizacion_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """El cliente aprobó. Valida que la cotización siga vigente."""
    cot = await _get_cotizacion_or_404(db, cotizacion_id)
    if cot.estado not in (EstadoCotizacion.BORRADOR, EstadoCotizacion.ENVIADA):
        raise HTTPException(
            status_code=400, detail="Solo se pueden aprobar cotizaciones en Borrador o Enviadas")
    if cot.fecha_vencimiento < date.today():
        raise HTTPException(
            status_code=400,
            detail=f"La cotización venció el {cot.fecha_vencimiento.isoformat()}. "
                   "Crea una nueva cotización con precios vigentes.",
        )
    cot.estado = EstadoCotizacion.APROBADA
    await db.flush()
    return _build_cotizacion_response(cot)


@router.post("/cotizaciones/{cotizacion_id}/rechazar", response_model=CotizacionResponse)
async def rechazar_cotizacion(
    cotizacion_id: int,
    _: CurrentUser,
    data: CotizacionRechazo | None = None,
    db: AsyncSession = Depends(get_db),
):
    """El cliente rechazó (o se descarta internamente)."""
    cot = await _get_cotizacion_or_404(db, cotizacion_id)
    if cot.estado not in (EstadoCotizacion.BORRADOR, EstadoCotizacion.ENVIADA):
        raise HTTPException(
            status_code=400, detail="Solo se pueden rechazar cotizaciones en Borrador o Enviadas")
    cot.estado = EstadoCotizacion.RECHAZADA
    if data and data.motivo:
        cot.motivo_rechazo = data.motivo
    await db.flush()
    return _build_cotizacion_response(cot)


@router.post("/cotizaciones/{cotizacion_id}/convertir", response_model=CotizacionResponse)
async def convertir_cotizacion(
    cotizacion_id: int, current: CurrentUser, db: AsyncSession = Depends(get_db)
):
    """Convertir una cotización Aprobada en un documento de venta (Borrador).
    Reusa el flujo de creación de ventas: la venta nace sin efectos de
    inventario/contabilidad hasta que se confirme."""
    cot = await _get_cotizacion_or_404(db, cotizacion_id)
    if cot.estado != EstadoCotizacion.APROBADA:
        raise HTTPException(
            status_code=400, detail="Solo se pueden convertir cotizaciones Aprobadas")

    venta_data = VentaCreate(
        fecha=date.today(),
        cliente_id=cot.cliente_id,
        vendedor=cot.vendedor,
        observaciones=(
            f"Generada desde cotización {cot.numero}"
            + (f"\n{cot.observaciones}" if cot.observaciones else "")
        ),
        detalles=[
            VentaDetalleCreate(
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
                descuento_porcentaje=d.descuento_porcentaje,
                iva_porcentaje=d.iva_porcentaje,
                notas=d.notas,
            )
            for d in cot.detalles
        ],
    )
    venta_resp = await create_venta(venta_data, current, db)

    cot.estado = EstadoCotizacion.CONVERTIDA
    cot.venta_id = venta_resp.id
    await db.flush()
    # La relación .venta ya estaba cargada como None en el identity map;
    # refrescarla para que la respuesta traiga el número de la venta creada.
    await db.refresh(cot, attribute_names=["venta"])
    return _build_cotizacion_response(cot)


# ══════════════════════════════════════════════════════════
# VENTAS (DOCUMENTOS) — CRUD
# ══════════════════════════════════════════════════════════

@router.get("/", response_model=List[VentaResponse])
async def list_ventas(
    _: CurrentUser,
    estado: Optional[EstadoVenta] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Listar documentos de venta (paginado: limit/offset, más recientes primero)."""
    query = for_tenant(
        select(VentaDocumento)
        .options(*_VENTA_EAGER)
        .order_by(desc(VentaDocumento.fecha), desc(VentaDocumento.id))
        .limit(limit)
        .offset(offset),
        VentaDocumento,
    )
    if estado:
        query = query.where(VentaDocumento.estado == estado)
    result = await db.execute(query)
    ventas = result.scalars().all()

    return [_build_venta_response(venta) for venta in ventas]


@router.get("/{venta_id}", response_model=VentaResponse)
async def get_venta(venta_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Obtener un documento de venta por ID con detalles."""
    venta = await db.scalar(
        for_tenant(
            select(VentaDocumento).options(*_VENTA_EAGER).where(VentaDocumento.id == venta_id),
            VentaDocumento,
        )
    )
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    return _build_venta_response(venta)


@router.post("/", response_model=VentaResponse, status_code=201)
async def create_venta(data: VentaCreate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Crear un nuevo documento de venta con detalles. Calcula totales automáticamente."""
    if not data.detalles:
        raise HTTPException(status_code=400, detail="La venta debe tener al menos una línea de detalle")

    # Verificar cliente
    cliente = await db.get(Cliente, data.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Generar número de venta
    numero = await _next_venta_numero(db)

    # Crear cabecera
    venta = VentaDocumento(
        numero=numero,
        fecha=data.fecha,
        fecha_vencimiento=data.fecha_vencimiento,
        cliente_id=data.cliente_id,
        centro_costo_id=data.centro_costo_id,
        vendedor=data.vendedor,
        observaciones=data.observaciones,
        estado=EstadoVenta.BORRADOR,
        estado_pago=EstadoPago.PENDIENTE,
    )
    db.add(venta)
    await db.flush()

    # Crear detalles y calcular totales
    subtotal_total = Decimal("0.00")
    descuento_total = Decimal("0.00")
    iva_total = Decimal("0.00")

    for det_data in data.detalles:
        # Verificar producto
        producto = await db.get(Producto, det_data.producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail=f"Producto ID {det_data.producto_id} no encontrado")

        calc = _calcular_detalle(det_data)

        detalle = VentaDetalle(
            venta_id=venta.id,
            producto_id=det_data.producto_id,
            cantidad=det_data.cantidad,
            precio_unitario=det_data.precio_unitario,
            descuento_porcentaje=det_data.descuento_porcentaje,
            subtotal_linea=calc["subtotal_linea"],
            iva_porcentaje=det_data.iva_porcentaje,
            iva_valor=calc["iva_valor"],
            total_linea=calc["total_linea"],
            notas=det_data.notas,
        )
        db.add(detalle)

        linea_bruta = det_data.cantidad * det_data.precio_unitario
        subtotal_total += linea_bruta
        desc_valor = linea_bruta * (det_data.descuento_porcentaje / Decimal("100"))
        descuento_total += desc_valor
        iva_total += calc["iva_valor"]

    base_gravable = subtotal_total - descuento_total

    # Retenciones: sugerencia según el perfil tributario del cliente + tarifas
    # vigentes, con override manual por factura (si el payload trae el valor, manda).
    sug_rf, sug_ri, sug_ic = await _sugerir_retenciones(db, cliente, base_gravable, iva_total)
    retefuente = data.retefuente if data.retefuente is not None else sug_rf
    reteiva = data.reteiva if data.reteiva is not None else sug_ri
    reteica = data.reteica if data.reteica is not None else sug_ic
    total = base_gravable + iva_total - retefuente - reteiva - reteica

    # Actualizar totales de cabecera
    venta.subtotal = round(subtotal_total, 2)
    venta.descuento_total = round(descuento_total, 2)
    venta.base_gravable = round(base_gravable, 2)
    venta.iva_total = round(iva_total, 2)
    venta.retefuente = retefuente
    venta.reteiva = reteiva
    venta.reteica = reteica
    venta.total = round(total, 2)

    await db.flush()

    # Respuesta unificada vía get_venta (mismo builder + eager load) — evita
    # duplicar el armado del VentaResponse.
    return await get_venta(venta.id, _, db)


@router.post("/{venta_id}/confirmar", response_model=VentaResponse)
async def confirmar_venta(venta_id: int, current: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Confirmar un documento de venta (pasa de Borrador a Confirmada)."""
    venta = await db.get(VentaDocumento, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado != EstadoVenta.BORRADOR:
        raise HTTPException(status_code=400, detail="Solo se pueden confirmar ventas en estado Borrador")

    try:
        await ventas_service.confirmar_venta(db, venta, current)
    except ventas_service.VentaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return await get_venta(venta_id, current, db)


@router.post("/{venta_id}/anular")
async def anular_venta(venta_id: int, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Anular un documento de venta."""
    venta = await db.get(VentaDocumento, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == EstadoVenta.ANULADA:
        raise HTTPException(status_code=400, detail="La venta ya está anulada")

    try:
        await ventas_service.anular_venta(db, venta, current)
    except ventas_service.VentaError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"detail": f"Venta {venta.numero} anulada correctamente"}


# ══════════════════════════════════════════════════════════
# DEVOLUCIONES — Nota crédito (NC-####)
# ══════════════════════════════════════════════════════════

@router.get("/{venta_id}/devoluciones", response_model=List[DevolucionResponse])
async def list_devoluciones_venta(venta_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(DevolucionVenta)
        .options(selectinload(DevolucionVenta.detalles))
        .where(DevolucionVenta.venta_id == venta_id)
        .order_by(DevolucionVenta.id)
    )).scalars().all()
    return rows


@router.post("/{venta_id}/devoluciones", response_model=DevolucionResponse, status_code=201)
async def crear_devolucion_venta(
    venta_id: int,
    data: DevolucionCreate,
    current: AdminOrAdministradoraDep,
    db: AsyncSession = Depends(get_db),
):
    """
    Nota crédito: devolución parcial o total de una venta confirmada/facturada.
    Reingresa el inventario, reduce la CxC y genera el asiento contable
    (DB 417501 Devoluciones + 240801 IVA / CR 130505 Clientes).
    """
    venta = await db.scalar(
        select(VentaDocumento)
        .options(selectinload(VentaDocumento.detalles))
        .where(VentaDocumento.id == venta_id)
    )
    if not venta:
        raise HTTPException(404, "Venta no encontrada")
    if venta.estado not in (EstadoVenta.CONFIRMADA, EstadoVenta.FACTURADA):
        raise HTTPException(400, "Solo se pueden devolver ventas Confirmadas o Facturadas")

    detalles_venta = {d.id: d for d in venta.detalles}

    # Cantidades ya devueltas por línea (devoluciones previas)
    ya_devueltas: dict[int, Decimal] = {}
    previas = (await db.execute(
        select(DevolucionVentaDetalle.venta_detalle_id, func.sum(DevolucionVentaDetalle.cantidad))
        .join(DevolucionVenta, DevolucionVenta.id == DevolucionVentaDetalle.devolucion_id)
        .where(DevolucionVenta.venta_id == venta_id)
        .group_by(DevolucionVentaDetalle.venta_detalle_id)
    )).all()
    for det_id, cant in previas:
        ya_devueltas[det_id] = Decimal(str(cant))

    numero = await next_sequential_numero(db, DevolucionVenta.numero, "NC")
    devolucion = DevolucionVenta(
        numero=numero,
        venta_id=venta.id,
        fecha=data.fecha or date.today(),
        motivo=data.motivo,
        usuario_id=current.id,
    )
    db.add(devolucion)
    await db.flush()

    subtotal = Decimal("0.00")
    iva_total = Decimal("0.00")
    for item in data.detalles:
        det = detalles_venta.get(item.venta_detalle_id)
        if not det:
            raise HTTPException(404, f"La línea {item.venta_detalle_id} no pertenece a esta venta")
        disponible = det.cantidad - ya_devueltas.get(det.id, Decimal("0"))
        if item.cantidad > disponible:
            raise HTTPException(
                400,
                f"No se puede devolver {item.cantidad} de la línea {det.id}: "
                f"vendidas {det.cantidad}, ya devueltas {ya_devueltas.get(det.id, 0)} "
                f"(máximo {disponible})",
            )

        # Montos con el precio, descuento e IVA de la línea original
        base = (item.cantidad * det.precio_unitario
                * (Decimal("1") - det.descuento_porcentaje / Decimal("100")))
        base = base.quantize(Decimal("0.01"))
        iva = (base * det.iva_porcentaje / Decimal("100")).quantize(Decimal("0.01"))
        subtotal += base
        iva_total += iva

        db.add(DevolucionVentaDetalle(
            devolucion_id=devolucion.id,
            venta_detalle_id=det.id,
            producto_id=det.producto_id,
            cantidad=item.cantidad,
            precio_unitario=det.precio_unitario,
            subtotal_linea=base,
            iva_valor=iva,
            total_linea=base + iva,
        ))

        # La mercancía devuelta reingresa al inventario
        prod = await db.get(Producto, det.producto_id)
        if prod and prod.controla_lote:
            # Reingresa a los mismos lotes de los que salió por FEFO
            await revertir_por_lotes(
                db,
                producto_id=det.producto_id,
                cantidad=item.cantidad,
                tipo_reverso=TipoMovimientoInventario.ENTRADA,
                origen=OrigenMovimiento.DEVOLUCION_VENTA,
                venta_id=venta.id,
                venta_detalle_id=det.id,
                motivo=f"Devolución {numero} de venta {venta.numero}: {data.motivo}",
                usuario_id=current.id,
            )
        else:
            await registrar_movimiento(
                db,
                producto_id=det.producto_id,
                tipo=TipoMovimientoInventario.ENTRADA,
                origen=OrigenMovimiento.DEVOLUCION_VENTA,
                cantidad=item.cantidad,
                motivo=f"Devolución {numero} de venta {venta.numero}: {data.motivo}",
                usuario_id=current.id,
                venta_id=venta.id,
                venta_detalle_id=det.id,
            )

    devolucion.subtotal = subtotal
    devolucion.iva_total = iva_total
    devolucion.total = subtotal + iva_total

    # Reducir la CxC de la factura. Si el cliente ya había pagado más de lo
    # que queda tras la devolución, la CxC queda Pagada y el saldo a favor
    # se gestiona manualmente (limitación documentada).
    cxc = await db.scalar(
        select(CuentaPorCobrar).where(CuentaPorCobrar.numero_factura == venta.numero)
    )
    if cxc and cxc.estado != EstadoDocumento.ANULADO:
        cxc.valor_factura = max(cxc.valor_factura - devolucion.total, Decimal("0"))
        saldo = cxc.valor_factura - (cxc.abonos or Decimal("0"))
        if saldo <= 0:
            cxc.estado = EstadoDocumento.PAGADO
        elif (cxc.abonos or Decimal("0")) > 0:
            cxc.estado = EstadoDocumento.PARCIAL
        else:
            cxc.estado = EstadoDocumento.PENDIENTE
        cxc.notas = ((cxc.notas or "") + f"\n[NC] {numero}: -{devolucion.total}").strip()

    # Asiento contable de la nota crédito (valida período abierto)
    await asiento_devolucion_venta(db, devolucion, venta, usuario_id=current.id)

    await db.flush()

    result = await db.scalar(
        select(DevolucionVenta)
        .options(selectinload(DevolucionVenta.detalles))
        .where(DevolucionVenta.id == devolucion.id)
    )
    return result
