"""
Super Ozono Global — API Routes (Ventas & Comercial)
CRUD completo para Productos, Clientes y Documentos de Venta
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, desc
from typing import List, Optional
from decimal import Decimal
from datetime import date, datetime

from app.core.database import get_db
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

router = APIRouter(prefix="/api/v1/ventas", tags=["Ventas & Comercial"])


# ══════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════

async def _next_venta_numero(db: AsyncSession) -> str:
    """Genera el siguiente número de venta: SOG-V-0001, SOG-V-0002..."""
    result = await db.scalar(
        select(func.count(VentaDocumento.id))
    )
    next_num = (result or 0) + 1
    return f"SOG-V-{next_num:04d}"


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


# ══════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=VentaDashboardStats)
async def get_ventas_dashboard(db: AsyncSession = Depends(get_db)):
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
        select(func.count(Cliente.id)).where(Cliente.activo == True)
    )
    productos_activos = await db.scalar(
        select(func.count(Producto.id)).where(Producto.activo == True)
    )

    # Productos con stock bajo
    stock_bajo = await db.scalar(
        select(func.count(Producto.id))
        .where(Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo)
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
        .join(VentaDocumento, VentaDocumento.id == VentaDetalle.venta_id, isouter=True)
        .where(Producto.activo == True)
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
    marca: Optional[str] = Query(None, description="Filtrar por marca"),
    activo: Optional[bool] = Query(None, description="Filtrar por estado activo"),
    db: AsyncSession = Depends(get_db),
):
    """Listar productos con filtros opcionales."""
    query = select(Producto).order_by(Producto.marca, Producto.nombre)
    if marca:
        query = query.where(Producto.marca == marca)
    if activo is not None:
        query = query.where(Producto.activo == activo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
async def get_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
    """Obtener un producto por ID."""
    producto = await db.get(Producto, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("/productos", response_model=ProductoResponse, status_code=201)
async def create_producto(data: ProductoCreate, db: AsyncSession = Depends(get_db)):
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
    producto_id: int, data: ProductoUpdate, db: AsyncSession = Depends(get_db)
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
async def delete_producto(producto_id: int, db: AsyncSession = Depends(get_db)):
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
    activo: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Listar clientes comerciales."""
    query = select(Cliente).order_by(Cliente.razon_social)
    if activo is not None:
        query = query.where(Cliente.activo == activo)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
async def get_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    """Obtener un cliente por ID."""
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


@router.post("/clientes", response_model=ClienteResponse, status_code=201)
async def create_cliente(data: ClienteCreate, db: AsyncSession = Depends(get_db)):
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
    cliente_id: int, data: ClienteUpdate, db: AsyncSession = Depends(get_db)
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
async def delete_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
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
    estado: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Listar documentos de venta."""
    query = select(VentaDocumento).order_by(desc(VentaDocumento.fecha), desc(VentaDocumento.id))
    if estado:
        query = query.where(VentaDocumento.estado == estado)
    result = await db.execute(query)
    ventas = result.scalars().all()

    # Enriquecer con datos de cliente y detalles
    response = []
    for venta in ventas:
        cliente = await db.get(Cliente, venta.cliente_id)
        # Cargar detalles
        detalles_result = await db.execute(
            select(VentaDetalle).where(VentaDetalle.venta_id == venta.id)
        )
        detalles_raw = detalles_result.scalars().all()

        detalles_resp = []
        for d in detalles_raw:
            prod = await db.get(Producto, d.producto_id)
            detalles_resp.append(VentaDetalleResponse(
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
                producto_nombre=prod.nombre if prod else None,
                producto_sku=prod.sku if prod else None,
            ))

        response.append(VentaResponse(
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
        ))

    return response


@router.get("/{venta_id}", response_model=VentaResponse)
async def get_venta(venta_id: int, db: AsyncSession = Depends(get_db)):
    """Obtener un documento de venta por ID con detalles."""
    venta = await db.get(VentaDocumento, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    cliente = await db.get(Cliente, venta.cliente_id)
    detalles_result = await db.execute(
        select(VentaDetalle).where(VentaDetalle.venta_id == venta.id)
    )
    detalles_raw = detalles_result.scalars().all()

    detalles_resp = []
    for d in detalles_raw:
        prod = await db.get(Producto, d.producto_id)
        detalles_resp.append(VentaDetalleResponse(
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
            producto_nombre=prod.nombre if prod else None,
            producto_sku=prod.sku if prod else None,
        ))

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


@router.post("/", response_model=VentaResponse, status_code=201)
async def create_venta(data: VentaCreate, db: AsyncSession = Depends(get_db)):
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

    # Calcular retenciones (ejemplo basado en parámetros tributarios colombianos)
    base_gravable = subtotal_total - descuento_total
    retefuente = round(base_gravable * Decimal("0.025"), 2) if base_gravable >= Decimal("1092000") else Decimal("0.00")
    reteiva = round(iva_total * Decimal("0.15"), 2) if iva_total > 0 else Decimal("0.00")
    total = base_gravable + iva_total - retefuente - reteiva

    # Actualizar totales de cabecera
    venta.subtotal = round(subtotal_total, 2)
    venta.descuento_total = round(descuento_total, 2)
    venta.base_gravable = round(base_gravable, 2)
    venta.iva_total = round(iva_total, 2)
    venta.retefuente = retefuente
    venta.reteiva = reteiva
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
async def confirmar_venta(venta_id: int, db: AsyncSession = Depends(get_db)):
    """Confirmar un documento de venta (pasa de Borrador a Confirmada)."""
    venta = await db.get(VentaDocumento, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado != EstadoVenta.BORRADOR:
        raise HTTPException(status_code=400, detail="Solo se pueden confirmar ventas en estado Borrador")

    venta.estado = EstadoVenta.CONFIRMADA
    await db.flush()
    await db.refresh(venta)

    # Re-fetch for response (reuse get_venta logic)
    return await get_venta(venta_id, db)


@router.post("/{venta_id}/anular")
async def anular_venta(venta_id: int, db: AsyncSession = Depends(get_db)):
    """Anular un documento de venta."""
    venta = await db.get(VentaDocumento, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado == EstadoVenta.ANULADA:
        raise HTTPException(status_code=400, detail="La venta ya está anulada")

    venta.estado = EstadoVenta.ANULADA
    await db.flush()
    return {"detail": f"Venta {venta.numero} anulada correctamente"}
