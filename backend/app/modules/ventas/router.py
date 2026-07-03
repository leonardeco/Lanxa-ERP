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
from datetime import date

from app.core.database import get_db
from app.core.config import get_settings
from app.core.numbering import next_sequential_numero
from app.api.deps import CurrentUser, AdminOrAdministradoraDep
from app.modules.ventas.models import (
    Producto, Cliente, VentaDocumento, VentaDetalle,
    EstadoVenta, EstadoPago,
)
from app.modules.ventas.schemas import (
    ProductoCreate, ProductoUpdate, ProductoResponse,
    ClienteCreate, ClienteUpdate, ClienteResponse,
    VentaCreate, VentaResponse, VentaDetalleResponse,
    VentaDashboardStats,
)
from app.modules.inventario.models import TipoMovimientoInventario, OrigenMovimiento
from app.modules.inventario.service import registrar_movimiento
from app.modules.contabilidad.models import CuentaPorCobrar, EstadoDocumento, ParametroTributario
from app.modules.contabilidad.asientos import asiento_venta_confirmada, reversar_asientos

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
        estado=venta.estado.value if hasattr(venta.estado, 'value') else venta.estado,
        estado_pago=venta.estado_pago.value if hasattr(venta.estado_pago, 'value') else venta.estado_pago,
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
    query = select(Producto).order_by(Producto.marca, Producto.nombre).limit(limit).offset(offset)
    if marca:
        query = query.where(Producto.marca == marca)
    if activo is not None:
        query = query.where(Producto.activo == activo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
async def get_producto(producto_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Obtener un producto por ID."""
    producto = await db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("/productos", response_model=ProductoResponse, status_code=201)
async def create_producto(data: ProductoCreate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Crear un nuevo producto."""
    # Verificar SKU único
    existing = await db.scalar(select(Producto.id).where(Producto.sku == data.sku))
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un producto con SKU '{data.sku}'")

    producto = Producto(**data.model_dump())
    db.add(producto)
    await db.flush()
    await db.refresh(producto)
    return producto


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
async def update_producto(
    producto_id: int, data: ProductoUpdate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)
):
    """Actualizar un producto existente."""
    producto = await db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(producto, field, value)

    await db.flush()
    await db.refresh(producto)
    return producto


@router.delete("/productos/{producto_id}")
async def delete_producto(producto_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Desactivar un producto (soft delete)."""
    producto = await db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    producto.activo = False
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
    query = select(Cliente).order_by(Cliente.razon_social).limit(limit).offset(offset)
    if activo is not None:
        query = query.where(Cliente.activo == activo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
async def get_cliente(cliente_id: int, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Obtener un cliente por ID."""
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.post("/clientes", response_model=ClienteResponse, status_code=201)
async def create_cliente(data: ClienteCreate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Crear un nuevo cliente."""
    existing = await db.scalar(select(Cliente.id).where(Cliente.nit_cc == data.nit_cc))
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un cliente con NIT/CC '{data.nit_cc}'")

    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    await db.flush()
    await db.refresh(cliente)
    return cliente


@router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
async def update_cliente(
    cliente_id: int, data: ClienteUpdate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)
):
    """Actualizar un cliente existente."""
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cliente, field, value)

    await db.flush()
    await db.refresh(cliente)
    return cliente


@router.delete("/clientes/{cliente_id}")
async def delete_cliente(cliente_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Desactivar un cliente (soft delete)."""
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    cliente.activo = False
    await db.flush()
    return {"detail": f"Cliente '{cliente.razon_social}' desactivado correctamente"}


# ══════════════════════════════════════════════════════════
# VENTAS (DOCUMENTOS) — CRUD
# ══════════════════════════════════════════════════════════

@router.get("/", response_model=List[VentaResponse])
async def list_ventas(
    _: CurrentUser,
    estado: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Listar documentos de venta (paginado: limit/offset, más recientes primero)."""
    query = (
        select(VentaDocumento)
        .options(*_VENTA_EAGER)
        .order_by(desc(VentaDocumento.fecha), desc(VentaDocumento.id))
        .limit(limit)
        .offset(offset)
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
        select(VentaDocumento).options(*_VENTA_EAGER).where(VentaDocumento.id == venta_id)
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
    detalles_resp = []

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
        await db.flush()

        linea_bruta = det_data.cantidad * det_data.precio_unitario
        subtotal_total += linea_bruta
        desc_valor = linea_bruta * (det_data.descuento_porcentaje / Decimal("100"))
        descuento_total += desc_valor
        iva_total += calc["iva_valor"]

        detalles_resp.append(VentaDetalleResponse(
            id=detalle.id,
            producto_id=detalle.producto_id,
            cantidad=detalle.cantidad,
            precio_unitario=detalle.precio_unitario,
            descuento_porcentaje=detalle.descuento_porcentaje,
            subtotal_linea=detalle.subtotal_linea,
            iva_porcentaje=detalle.iva_porcentaje,
            iva_valor=detalle.iva_valor,
            total_linea=detalle.total_linea,
            notas=detalle.notas,
            created_at=detalle.created_at,
            producto_nombre=producto.nombre,
            producto_sku=producto.sku,
        ))

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
    await db.refresh(venta)

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
        estado=venta.estado.value if hasattr(venta.estado, 'value') else venta.estado,
        estado_pago=venta.estado_pago.value if hasattr(venta.estado_pago, 'value') else venta.estado_pago,
        observaciones=venta.observaciones,
        created_at=venta.created_at,
        updated_at=venta.updated_at,
        cliente_razon_social=cliente.razon_social,
        cliente_nit=cliente.nit_cc,
        detalles=detalles_resp,
    )


@router.post("/{venta_id}/confirmar", response_model=VentaResponse)
async def confirmar_venta(venta_id: int, current: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Confirmar un documento de venta (pasa de Borrador a Confirmada)."""
    venta = await db.get(VentaDocumento, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado != EstadoVenta.BORRADOR:
        raise HTTPException(status_code=400, detail="Solo se pueden confirmar ventas en estado Borrador")

    # Validar stock disponible ANTES de confirmar y descontar (evita sobreventa)
    detalles = (await db.execute(select(VentaDetalle).where(VentaDetalle.venta_id == venta.id))).scalars().all()
    faltantes = []
    for d in detalles:
        prod = await db.get(Producto, d.producto_id)
        requerido = d.cantidad
        disponible = prod.stock_actual if (prod and prod.stock_actual is not None) else Decimal("0")
        if disponible < requerido:
            nombre = prod.nombre if prod else f"Producto {d.producto_id}"
            faltantes.append(f"{nombre} (disponible: {disponible}, requerido: {requerido})")
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail="Stock insuficiente para confirmar la venta: " + "; ".join(faltantes),
        )

    venta.estado = EstadoVenta.CONFIRMADA

    # Salidas automáticas de inventario por cada línea
    for d in detalles:
        await registrar_movimiento(
            db,
            producto_id=d.producto_id,
            tipo=TipoMovimientoInventario.SALIDA,
            origen=OrigenMovimiento.VENTA,
            cantidad=d.cantidad,
            motivo=f"Salida por venta {venta.numero}",
            usuario_id=current.id,
            venta_id=venta.id,
            venta_detalle_id=d.id,
        )

    # Crear CxC automáticamente (espejo de compras→CxP), si no existe ya una
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
    await asiento_venta_confirmada(db, venta, usuario_id=current.id)

    await db.flush()
    await db.refresh(venta)

    # Re-fetch for response (reuse get_venta logic)
    return await get_venta(venta_id, current, db)


@router.post("/{venta_id}/anular")
async def anular_venta(venta_id: int, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Anular un documento de venta."""
    venta = await db.get(VentaDocumento, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == EstadoVenta.ANULADA:
        raise HTTPException(status_code=400, detail="La venta ya está anulada")

    estado_anterior = venta.estado
    venta.estado = EstadoVenta.ANULADA

    # Si la venta ya había generado salidas de inventario, revertirlas
    if estado_anterior in (EstadoVenta.CONFIRMADA, EstadoVenta.FACTURADA):
        detalles_result = await db.execute(select(VentaDetalle).where(VentaDetalle.venta_id == venta.id))
        for d in detalles_result.scalars().all():
            await registrar_movimiento(
                db,
                producto_id=d.producto_id,
                tipo=TipoMovimientoInventario.ENTRADA,
                origen=OrigenMovimiento.REVERSO_VENTA,
                cantidad=d.cantidad,
                motivo=f"Reverso por anulación de venta {venta.numero}",
                usuario_id=current.id,
                venta_id=venta.id,
                venta_detalle_id=d.id,
            )

    # Reverso del asiento contable si la venta ya lo había generado
    await reversar_asientos(
        db, documento_ref=venta.numero, usuario_id=current.id,
        motivo=f"Anulación de venta {venta.numero}",
    )

    await db.flush()
    return {"detail": f"Venta {venta.numero} anulada correctamente"}
