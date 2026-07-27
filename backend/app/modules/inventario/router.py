from decimal import Decimal
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Response
from sqlalchemy import select, func, extract, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tenancy import for_tenant, get_for_tenant, tenant_clause
from app.api.deps import CurrentUser, AdminOrAdministradoraDep
from app.modules.ventas.models import Producto

from . import importador
from .models import MovimientoInventario, TipoMovimientoInventario, OrigenMovimiento, Lote
from .schemas import (
    MovimientoResponse, AjusteInventarioInput, InventarioDashboard, TopProductoValor,
    ErrorFilaImport, PreviewImport, ResumenImport, LoteResponse,
)
from .service import registrar_movimiento
from .lotes import (
    entrada_lote, consumir_fefo, LoteError,
    estado_lote, dias_para_vencer, DIAS_ALERTA_DEFAULT,
)

router = APIRouter(prefix="/api/v1/inventario", tags=["Inventario"])


def _to_response(mov: MovimientoInventario, nombre: Optional[str], sku: Optional[str]) -> MovimientoResponse:
    return MovimientoResponse(
        id=mov.id,
        producto_id=mov.producto_id,
        producto_nombre=nombre,
        producto_sku=sku,
        tipo=mov.tipo.value if hasattr(mov.tipo, "value") else mov.tipo,
        origen=mov.origen.value if hasattr(mov.origen, "value") else mov.origen,
        cantidad=mov.cantidad,
        stock_antes=mov.stock_antes,
        stock_despues=mov.stock_despues,
        costo_unitario=mov.costo_unitario,
        compra_id=mov.compra_id,
        venta_id=mov.venta_id,
        motivo=mov.motivo,
        usuario_id=mov.usuario_id,
        fecha=mov.fecha,
        created_at=mov.created_at,
    )


# ══════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=InventarioDashboard)
async def get_dashboard(_: CurrentUser, session: AsyncSession = Depends(get_db)):
    hoy = date.today()

    valor_inventario = await session.scalar(
        select(func.coalesce(func.sum(Producto.stock_actual * func.coalesce(Producto.precio_costo, 0)), 0))
        .where(Producto.activo == True, tenant_clause(Producto))  # noqa: E712
    )

    stock_bajo = await session.scalar(
        select(func.count(Producto.id))
        .where(Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo, tenant_clause(Producto))  # noqa: E712
    )

    movimientos_mes = await session.scalar(
        select(func.count(MovimientoInventario.id))
        .where(
            extract("year", MovimientoInventario.fecha) == hoy.year,
            extract("month", MovimientoInventario.fecha) == hoy.month,
            tenant_clause(MovimientoInventario),
        )
    )

    top_result = await session.execute(
        select(
            Producto.nombre,
            Producto.sku,
            (Producto.stock_actual * func.coalesce(Producto.precio_costo, 0)).label("valor"),
        )
        .where(Producto.activo == True, tenant_clause(Producto))  # noqa: E712
        .order_by(desc("valor"))
        .limit(5)
    )
    top_productos = [
        TopProductoValor(producto=row[0], sku=row[1], valor=float(row[2] or 0))
        for row in top_result.all()
    ]

    # Alertas de vencimiento por lote (solo lotes activos con existencia y fecha)
    _lote_con_saldo = (
        Lote.activo.is_(True),
        Lote.cantidad_actual > 0,
        Lote.fecha_vencimiento.is_not(None),
        tenant_clause(Lote),
    )
    lotes_por_vencer = await session.scalar(
        select(func.count(Lote.id)).where(
            *_lote_con_saldo,
            Lote.fecha_vencimiento >= hoy,
            Lote.fecha_vencimiento <= hoy + timedelta(days=DIAS_ALERTA_DEFAULT),
        )
    )
    lotes_vencidos = await session.scalar(
        select(func.count(Lote.id)).where(*_lote_con_saldo, Lote.fecha_vencimiento < hoy)
    )

    return InventarioDashboard(
        valor_total_inventario=Decimal(str(valor_inventario or 0)),
        productos_stock_bajo=stock_bajo or 0,
        movimientos_mes=movimientos_mes or 0,
        top_productos_por_valor=top_productos,
        lotes_por_vencer=lotes_por_vencer or 0,
        lotes_vencidos=lotes_vencidos or 0,
    )


# ══════════════════════════════════════════════════════════
# LOTES — existencias y alertas de vencimiento (Capa 4)
# ══════════════════════════════════════════════════════════

@router.get("/lotes", response_model=List[LoteResponse])
async def list_lotes(
    _: CurrentUser,
    producto_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(
        None, description="vigente | por_vencer | vencido | sin_vencimiento"),
    dias: int = Query(DIAS_ALERTA_DEFAULT, ge=1, le=365,
                      description="Umbral de días para 'por_vencer'"),
    incluir_agotados: bool = Query(False),
    session: AsyncSession = Depends(get_db),
):
    """Existencias por lote con su estado de vencimiento derivado. Ordena por
    vencimiento (los que vencen antes primero; los sin fecha al final)."""
    hoy = date.today()
    query = for_tenant(
        select(Lote, Producto.nombre, Producto.sku)
        .join(Producto, Producto.id == Lote.producto_id)
        .order_by(Lote.fecha_vencimiento.is_(None), Lote.fecha_vencimiento, Lote.id),
        Lote,
    )
    if producto_id:
        query = query.where(Lote.producto_id == producto_id)
    if not incluir_agotados:
        query = query.where(Lote.activo.is_(True), Lote.cantidad_actual > 0)

    filas = (await session.execute(query)).all()
    respuestas = []
    for lote, nombre, sku in filas:
        est = estado_lote(lote.fecha_vencimiento, hoy, dias)
        if estado and est != estado:
            continue
        respuestas.append(LoteResponse(
            id=lote.id,
            producto_id=lote.producto_id,
            producto_nombre=nombre,
            producto_sku=sku,
            codigo_lote=lote.codigo_lote,
            fecha_vencimiento=lote.fecha_vencimiento,
            cantidad_actual=lote.cantidad_actual,
            costo_unitario=lote.costo_unitario,
            origen=lote.origen,
            activo=lote.activo,
            estado=est,
            dias_para_vencer=dias_para_vencer(lote.fecha_vencimiento, hoy),
        ))
    return respuestas


# ══════════════════════════════════════════════════════════
# MOVIMIENTOS (KARDEX)
# ══════════════════════════════════════════════════════════

@router.get("/movimientos", response_model=List[MovimientoResponse])
async def list_movimientos(
    _: CurrentUser,
    producto_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    origen: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    query = for_tenant(
        select(MovimientoInventario, Producto.nombre, Producto.sku)
        .join(Producto, Producto.id == MovimientoInventario.producto_id)
        .order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc()),
        MovimientoInventario,
    )
    if producto_id:
        query = query.where(MovimientoInventario.producto_id == producto_id)
    if tipo:
        query = query.where(MovimientoInventario.tipo == tipo)
    if origen:
        query = query.where(MovimientoInventario.origen == origen)
    if fecha_desde:
        query = query.where(MovimientoInventario.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.where(MovimientoInventario.fecha <= fecha_hasta)

    result = await session.execute(query)
    return [_to_response(mov, nombre, sku) for mov, nombre, sku in result.all()]


@router.get("/movimientos/{producto_id}", response_model=List[MovimientoResponse])
async def list_movimientos_producto(
    producto_id: int,
    current: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    return await list_movimientos(current, producto_id=producto_id, session=session)


# ══════════════════════════════════════════════════════════
# AJUSTE MANUAL
# ══════════════════════════════════════════════════════════

@router.post("/ajustes", response_model=MovimientoResponse, status_code=201)
async def crear_ajuste(
    data: AjusteInventarioInput,
    current: AdminOrAdministradoraDep,
    session: AsyncSession = Depends(get_db),
):
    producto = await get_for_tenant(session, Producto, data.producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    tipo = TipoMovimientoInventario.ENTRADA if data.tipo == "Entrada" else TipoMovimientoInventario.SALIDA

    # Un ajuste de salida no puede dejar stock negativo (ventas y devoluciones
    # ya validan; este era el único camino que permitía negativo en silencio)
    if tipo == TipoMovimientoInventario.SALIDA:
        disponible = producto.stock_actual if producto.stock_actual is not None else Decimal("0")
        if data.cantidad > disponible:
            raise HTTPException(
                status_code=400,
                detail=f"Stock insuficiente para el ajuste: disponible {disponible}, "
                       f"salida solicitada {data.cantidad}",
            )

    motivo = data.motivo or f"Ajuste manual de {data.tipo.lower()}"

    # Productos con control de lote: la entrada crea/incrementa un lote (requiere
    # código); la salida sale por FEFO. El resto usa el stock simple.
    if producto.controla_lote:
        try:
            if tipo == TipoMovimientoInventario.ENTRADA:
                if not (data.codigo_lote and data.codigo_lote.strip()):
                    raise HTTPException(
                        status_code=400,
                        detail=f"El producto '{producto.nombre}' controla lote: "
                               f"el ajuste de entrada necesita un código de lote.",
                    )
                _, mov = await entrada_lote(
                    session,
                    producto_id=data.producto_id,
                    cantidad=data.cantidad,
                    codigo_lote=data.codigo_lote,
                    fecha_vencimiento=data.fecha_vencimiento,
                    origen=OrigenMovimiento.AJUSTE_MANUAL,
                    usuario_id=current.id,
                    motivo=motivo,
                )
            else:
                movs = await consumir_fefo(
                    session,
                    producto_id=data.producto_id,
                    cantidad=data.cantidad,
                    origen=OrigenMovimiento.AJUSTE_MANUAL,
                    usuario_id=current.id,
                    motivo=motivo,
                )
                mov = movs[-1]
        except LoteError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    else:
        mov = await registrar_movimiento(
            session,
            producto_id=data.producto_id,
            tipo=tipo,
            origen=OrigenMovimiento.AJUSTE_MANUAL,
            cantidad=data.cantidad,
            motivo=motivo,
            usuario_id=current.id,
        )
    await session.commit()
    await session.refresh(mov)
    return _to_response(mov, producto.nombre, producto.sku)


# ══════════════════════════════════════════════════════════
# IMPORTADOR DE INVENTARIO INICIAL (#2)
# ══════════════════════════════════════════════════════════

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/plantilla")
async def descargar_plantilla(_: AdminOrAdministradoraDep):
    """Descarga la plantilla .xlsx en blanco para cargar el inventario inicial."""
    contenido = importador.generar_plantilla()
    return Response(
        content=contenido,
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": 'attachment; filename="plantilla-inventario-inicial.xlsx"'},
    )


@router.post("/importar")
async def importar_inventario(
    current: AdminOrAdministradoraDep,
    archivo: UploadFile = File(...),
    commit: bool = Query(False, description="false: solo previsualiza; true: importa si no hay errores"),
    session: AsyncSession = Depends(get_db),
):
    """Valida el .xlsx y (con commit=true y cero errores) crea los productos con su
    stock inicial. Todo o nada — con errores no se escribe nada."""
    contenido = await archivo.read()
    if len(contenido) > 5_000_000:  # ~5 MB: una plantilla real pesa pocos KB
        raise HTTPException(status_code=400, detail="El archivo es demasiado grande (máx. 5 MB).")
    try:
        resultado = await importador.validar(contenido, session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    errores = [ErrorFilaImport(fila=e.fila, columna=e.columna, mensaje=e.mensaje)
               for e in resultado.errores]

    if not commit:
        return PreviewImport(
            total_filas=resultado.total_filas,
            validas=len(resultado.filas_ok),
            errores=errores,
        )

    if errores:
        raise HTTPException(
            status_code=422,
            detail={"mensaje": "El archivo tiene errores; no se importó nada.",
                    "errores": [e.model_dump() for e in errores]},
        )

    resumen = await importador.importar(session, resultado.filas_ok, current)
    return ResumenImport(importados=resumen["creados"])
