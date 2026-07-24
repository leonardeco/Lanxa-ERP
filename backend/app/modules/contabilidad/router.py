"""
Super Ozono Global — API Routes (Contabilidad Núcleo)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date
from decimal import Decimal

from app.core.database import get_db
from app.core.config import get_settings
from app.core.numbering import next_sequential_numero
from app.core.tenancy import for_tenant, get_for_tenant, tenant_clause
from app.api.deps import CurrentUser, ContableDep
from app.modules.contabilidad.models import (
    PlanCuentas, CentroCosto, PeriodoContable, Tercero,
    ParametroTributario, ParametroNomina,
    CuentaPorCobrar, CuentaPorPagar, EstadoDocumento,
    Pago, TipoPago, EstadoPeriodo,
)
from app.modules.compras.models import CompraDocumento
from app.modules.contabilidad.models import AsientoContable, MovimientoAsiento
from app.modules.contabilidad.asientos import asiento_abono_cxc, asiento_abono_cxp, reversar_asientos
from app.modules.auditoria.service import registrar_auditoria, diff_cambios
from app.modules.contabilidad.schemas import (
    PlanCuentasCreate, PlanCuentasUpdate, PlanCuentasResponse,
    CentroCostoCreate, CentroCostoUpdate, CentroCostoResponse,
    PeriodoContableCreate, PeriodoContableResponse,
    TerceroResponse,
    ParametroTributarioUpdate, ParametroTributarioResponse,
    ParametroNominaUpdate, ParametroNominaResponse,
    DashboardStats,
    CxCCreate, CxCUpdate, CxCResponse, AbonoCreate,
    CxPCreate, CxPUpdate, CxPResponse, CarteraStats,
    PagoResponse, AbonoCxCResultado, AbonoCxPResultado,
    AsientoResponse, MovimientoAsientoResponse,
    MovimientoAuxiliar, AuxiliarTerceroResponse,
)

router = APIRouter(prefix="/api/v1/contabilidad", tags=["Contabilidad"])
settings = get_settings()


# ── Dashboard Stats ──────────────────────────────────────

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(_: ContableDep, db: AsyncSession = Depends(get_db)):
    """Estadísticas generales del módulo contable."""
    cuentas = await db.scalar(select(func.count(PlanCuentas.id)).where(tenant_clause(PlanCuentas)))
    centros = await db.scalar(select(func.count(CentroCosto.id)).where(tenant_clause(CentroCosto)))
    periodos = await db.scalar(select(func.count(PeriodoContable.id)).where(tenant_clause(PeriodoContable)))
    terceros = await db.scalar(select(func.count(Tercero.id)).where(tenant_clause(Tercero)))
    tributarios = await db.scalar(select(func.count(ParametroTributario.id)).where(tenant_clause(ParametroTributario)))
    nomina = await db.scalar(select(func.count(ParametroNomina.id)).where(tenant_clause(ParametroNomina)))

    return DashboardStats(
        total_cuentas_puc=cuentas or 0,
        total_centros_costo=centros or 0,
        total_periodos=periodos or 0,
        total_terceros=terceros or 0,
        total_parametros_tributarios=tributarios or 0,
        total_parametros_nomina=nomina or 0,
        empresa_nit=settings.EMPRESA_NIT,
        empresa_razon_social=settings.EMPRESA_RAZON_SOCIAL,
    )


# ── Plan de Cuentas (PUC) ───────────────────────────────

@router.get("/puc", response_model=List[PlanCuentasResponse])
async def list_plan_cuentas(_: ContableDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        for_tenant(select(PlanCuentas).order_by(PlanCuentas.codigo_puc), PlanCuentas)
    )
    return result.scalars().all()


@router.get("/puc/{codigo}", response_model=PlanCuentasResponse)
async def get_cuenta_puc(codigo: str, _: ContableDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PlanCuentas).where(
            PlanCuentas.codigo_puc == codigo, tenant_clause(PlanCuentas)
        )
    )
    cuenta = result.scalar_one_or_none()
    if not cuenta:
        raise HTTPException(status_code=404, detail=f"Cuenta PUC {codigo} no encontrada")
    return cuenta


@router.post("/puc", response_model=PlanCuentasResponse, status_code=201)
async def create_cuenta_puc(
    body: PlanCuentasCreate, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    existing = await db.scalar(
        select(PlanCuentas).where(
            PlanCuentas.codigo_puc == body.codigo_puc, tenant_clause(PlanCuentas)
        )
    )
    if existing:
        raise HTTPException(400, f"Ya existe la cuenta PUC {body.codigo_puc}")
    cuenta = PlanCuentas(**body.model_dump())
    db.add(cuenta)
    await db.flush()
    registrar_auditoria(db, current, "Crear", "PlanCuentas", cuenta.id,
                        f"Cuenta PUC {cuenta.codigo_puc} — {cuenta.nombre}")
    await db.commit()
    await db.refresh(cuenta)
    return cuenta


@router.put("/puc/{cuenta_id}", response_model=PlanCuentasResponse)
async def update_cuenta_puc(
    cuenta_id: int, body: PlanCuentasUpdate, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    cuenta = await get_for_tenant(db, PlanCuentas, cuenta_id)
    if not cuenta:
        raise HTTPException(404, "Cuenta PUC no encontrada")
    update_data = body.model_dump(exclude_none=True)
    cambios = diff_cambios(cuenta, update_data)
    for field, value in update_data.items():
        setattr(cuenta, field, value)
    if cambios:
        registrar_auditoria(db, current, "Actualizar", "PlanCuentas", cuenta.id,
                            f"Cuenta PUC {cuenta.codigo_puc} — {cuenta.nombre}", cambios)
    await db.commit()
    await db.refresh(cuenta)
    return cuenta


@router.patch("/puc/{cuenta_id}/toggle", response_model=PlanCuentasResponse)
async def toggle_cuenta_puc(cuenta_id: int, current: ContableDep, db: AsyncSession = Depends(get_db)):
    cuenta = await get_for_tenant(db, PlanCuentas, cuenta_id)
    if not cuenta:
        raise HTTPException(404, "Cuenta PUC no encontrada")
    cuenta.activo = not cuenta.activo
    registrar_auditoria(db, current, "Activar" if cuenta.activo else "Desactivar",
                        "PlanCuentas", cuenta.id,
                        f"Cuenta PUC {cuenta.codigo_puc} — {cuenta.nombre}")
    await db.commit()
    await db.refresh(cuenta)
    return cuenta


# ── Centros de Costo ─────────────────────────────────────

@router.get("/centros-costo", response_model=List[CentroCostoResponse])
async def list_centros_costo(_: ContableDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        for_tenant(select(CentroCosto).order_by(CentroCosto.codigo), CentroCosto)
    )
    return result.scalars().all()


@router.post("/centros-costo", response_model=CentroCostoResponse, status_code=201)
async def create_centro_costo(
    body: CentroCostoCreate, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    existing = await db.scalar(
        select(CentroCosto).where(CentroCosto.codigo == body.codigo, tenant_clause(CentroCosto))
    )
    if existing:
        raise HTTPException(400, f"Ya existe el centro de costo {body.codigo}")
    cc = CentroCosto(**body.model_dump())
    db.add(cc)
    await db.flush()
    registrar_auditoria(db, current, "Crear", "CentroCosto", cc.id,
                        f"Centro de costo {cc.codigo} — {cc.nombre}")
    await db.commit()
    await db.refresh(cc)
    return cc


@router.put("/centros-costo/{cc_id}", response_model=CentroCostoResponse)
async def update_centro_costo(
    cc_id: int, body: CentroCostoUpdate, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    cc = await get_for_tenant(db, CentroCosto, cc_id)
    if not cc:
        raise HTTPException(404, "Centro de costo no encontrado")
    update_data = body.model_dump(exclude_none=True)
    cambios = diff_cambios(cc, update_data)
    for field, value in update_data.items():
        setattr(cc, field, value)
    if cambios:
        registrar_auditoria(db, current, "Actualizar", "CentroCosto", cc.id,
                            f"Centro de costo {cc.codigo} — {cc.nombre}", cambios)
    await db.commit()
    await db.refresh(cc)
    return cc


@router.patch("/centros-costo/{cc_id}/toggle", response_model=CentroCostoResponse)
async def toggle_centro_costo(cc_id: int, current: ContableDep, db: AsyncSession = Depends(get_db)):
    cc = await get_for_tenant(db, CentroCosto, cc_id)
    if not cc:
        raise HTTPException(404, "Centro de costo no encontrado")
    cc.activo = not cc.activo
    registrar_auditoria(db, current, "Activar" if cc.activo else "Desactivar",
                        "CentroCosto", cc.id, f"Centro de costo {cc.codigo} — {cc.nombre}")
    await db.commit()
    await db.refresh(cc)
    return cc


# ── Períodos Contables ───────────────────────────────────

@router.get("/periodos", response_model=List[PeriodoContableResponse])
async def list_periodos(_: ContableDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        for_tenant(
            select(PeriodoContable).order_by(PeriodoContable.anio, PeriodoContable.mes),
            PeriodoContable,
        )
    )
    return result.scalars().all()


@router.post("/periodos", response_model=PeriodoContableResponse, status_code=201)
async def create_periodo(body: PeriodoContableCreate, _: ContableDep, db: AsyncSession = Depends(get_db)):
    periodo_str = f"{body.anio}-{body.mes:02d}"
    existing = await db.scalar(
        select(PeriodoContable).where(
            PeriodoContable.periodo == periodo_str, tenant_clause(PeriodoContable)
        )
    )
    if existing:
        raise HTTPException(400, f"El período {periodo_str} ya existe")
    periodo = PeriodoContable(
        anio=body.anio,
        mes=body.mes,
        periodo=periodo_str,
        estado=EstadoPeriodo.ABIERTO,
    )
    db.add(periodo)
    await db.commit()
    await db.refresh(periodo)
    return periodo


@router.patch("/periodos/{periodo_id}/toggle", response_model=PeriodoContableResponse)
async def toggle_periodo(periodo_id: int, current: ContableDep, db: AsyncSession = Depends(get_db)):
    periodo = await get_for_tenant(db, PeriodoContable, periodo_id)
    if not periodo:
        raise HTTPException(404, "Período no encontrado")
    if periodo.estado == EstadoPeriodo.ABIERTO:
        periodo.estado = EstadoPeriodo.CERRADO
        periodo.fecha_cierre = date.today()
        accion = "Cerrar"
    else:
        periodo.estado = EstadoPeriodo.ABIERTO
        periodo.fecha_cierre = None
        accion = "Reabrir"
    registrar_auditoria(db, current, accion, "PeriodoContable", periodo.id,
                        f"Período contable {periodo.periodo}")
    await db.commit()
    await db.refresh(periodo)
    return periodo


# ── Terceros ─────────────────────────────────────────────

@router.get("/terceros", response_model=List[TerceroResponse])
async def list_terceros(_: ContableDep, db: AsyncSession = Depends(get_db)):
    """Listar todos los terceros registrados."""
    result = await db.execute(
        for_tenant(select(Tercero).order_by(Tercero.razon_social), Tercero)
    )
    return result.scalars().all()


# ── Parámetros Tributarios ───────────────────────────────

@router.get("/parametros-tributarios", response_model=List[ParametroTributarioResponse])
async def list_parametros_tributarios(
    _: ContableDep,
    activo: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = for_tenant(select(ParametroTributario).order_by(ParametroTributario.concepto), ParametroTributario)
    if activo is not None:
        q = q.where(ParametroTributario.activo == activo)
    return (await db.execute(q)).scalars().all()


@router.put("/parametros-tributarios/{param_id}", response_model=ParametroTributarioResponse)
async def update_parametro_tributario(
    param_id: int, body: ParametroTributarioUpdate, current: ContableDep,
    db: AsyncSession = Depends(get_db),
):
    param = await get_for_tenant(db, ParametroTributario, param_id)
    if not param:
        raise HTTPException(404, "Parámetro tributario no encontrado")
    update_data = body.model_dump(exclude_none=True)
    cambios = diff_cambios(param, update_data)
    for field, value in update_data.items():
        setattr(param, field, value)
    if cambios:
        registrar_auditoria(db, current, "Actualizar", "ParametroTributario", param.id,
                            f"Parámetro tributario: {param.concepto}", cambios)
    await db.commit()
    await db.refresh(param)
    return param


@router.patch("/parametros-tributarios/{param_id}/toggle", response_model=ParametroTributarioResponse)
async def toggle_parametro_tributario(
    param_id: int, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    param = await get_for_tenant(db, ParametroTributario, param_id)
    if not param:
        raise HTTPException(404, "Parámetro tributario no encontrado")
    param.activo = not param.activo
    registrar_auditoria(db, current, "Activar" if param.activo else "Desactivar",
                        "ParametroTributario", param.id,
                        f"Parámetro tributario: {param.concepto}")
    await db.commit()
    await db.refresh(param)
    return param


# ── Parámetros de Nómina ─────────────────────────────────

@router.get("/parametros-nomina", response_model=List[ParametroNominaResponse])
async def list_parametros_nomina(
    _: ContableDep,
    activo: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = for_tenant(select(ParametroNomina).order_by(ParametroNomina.concepto), ParametroNomina)
    if activo is not None:
        q = q.where(ParametroNomina.activo == activo)
    return (await db.execute(q)).scalars().all()


@router.put("/parametros-nomina/{param_id}", response_model=ParametroNominaResponse)
async def update_parametro_nomina(
    param_id: int, body: ParametroNominaUpdate, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    param = await get_for_tenant(db, ParametroNomina, param_id)
    if not param:
        raise HTTPException(404, "Parámetro de nómina no encontrado")
    update_data = body.model_dump(exclude_none=True)
    cambios = diff_cambios(param, update_data)
    for field, value in update_data.items():
        setattr(param, field, value)
    if cambios:
        registrar_auditoria(db, current, "Actualizar", "ParametroNomina", param.id,
                            f"Parámetro de nómina: {param.concepto}", cambios)
    await db.commit()
    await db.refresh(param)
    return param


@router.patch("/parametros-nomina/{param_id}/toggle", response_model=ParametroNominaResponse)
async def toggle_parametro_nomina(param_id: int, current: ContableDep, db: AsyncSession = Depends(get_db)):
    param = await get_for_tenant(db, ParametroNomina, param_id)
    if not param:
        raise HTTPException(404, "Parámetro de nómina no encontrado")
    param.activo = not param.activo
    registrar_auditoria(db, current, "Activar" if param.activo else "Desactivar",
                        "ParametroNomina", param.id,
                        f"Parámetro de nómina: {param.concepto}")
    await db.commit()
    await db.refresh(param)
    return param


# ════════════════════════════════════════════════════════════
# CARTERA — Cuentas por Cobrar y por Pagar
# ════════════════════════════════════════════════════════════

def _dias_vencido(fecha_vencimiento, estado: str) -> int:
    if not fecha_vencimiento or estado in ("Pagado", "Anulado"):
        return 0
    delta = (date.today() - fecha_vencimiento).days
    return max(delta, 0)


async def _next_numero_comprobante(db: AsyncSession, prefijo: str) -> str:
    """Numeración secuencial por prefijo: RC-0001 (Recibo de Caja, CxC), CE-0001 (Comprobante de Egreso, CxP)."""
    return await next_sequential_numero(db, Pago.numero_comprobante, prefijo)


def _enrich_cxc(c: CuentaPorCobrar) -> CxCResponse:
    """Construcción explícita (13b): antes usaba {**c.__dict__}, frágil ante
    cambios de modelo y dependiente del estado interno de SQLAlchemy."""
    saldo = (c.valor_factura or Decimal("0")) - (c.abonos or Decimal("0"))
    return CxCResponse(
        id=c.id,
        numero_factura=c.numero_factura,
        fecha_emision=c.fecha_emision,
        cliente_nit=c.cliente_nit,
        nombre_cliente=c.nombre_cliente,
        marca=c.marca,
        valor_factura=c.valor_factura,
        abonos=c.abonos,
        saldo_pendiente=saldo,
        fecha_vencimiento=c.fecha_vencimiento,
        estado=c.estado.value if hasattr(c.estado, "value") else c.estado,
        dias_vencido=_dias_vencido(c.fecha_vencimiento, c.estado),
        notas=c.notas,
        created_at=c.created_at,
    )


def _enrich_cxp(p: CuentaPorPagar) -> CxPResponse:
    saldo = (p.valor or Decimal("0")) - (p.abonos or Decimal("0"))
    return CxPResponse(
        id=p.id,
        numero_documento=p.numero_documento,
        fecha=p.fecha,
        proveedor_nit=p.proveedor_nit,
        razon_social=p.razon_social,
        concepto=p.concepto,
        valor=p.valor,
        abonos=p.abonos,
        saldo_pendiente=saldo,
        fecha_vencimiento=p.fecha_vencimiento,
        estado=p.estado.value if hasattr(p.estado, "value") else p.estado,
        dias_vencido=_dias_vencido(p.fecha_vencimiento, p.estado),
        compra_id=p.compra_id,
        notas=p.notas,
        created_at=p.created_at,
    )


# -- Stats globales de cartera ---------------------------------

@router.get("/cartera/stats", response_model=CarteraStats)
async def cartera_stats(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    hoy = date.today()

    cxc_rows = (await db.execute(
        select(CuentaPorCobrar).where(
            CuentaPorCobrar.estado.notin_(["Pagado", "Anulado"]), tenant_clause(CuentaPorCobrar)
        )
    )).scalars().all()
    cxp_rows = (await db.execute(
        select(CuentaPorPagar).where(
            CuentaPorPagar.estado.notin_(["Pagado", "Anulado"]), tenant_clause(CuentaPorPagar)
        )
    )).scalars().all()

    cxc_pendiente = sum((r.valor_factura or 0) - (r.abonos or 0) for r in cxc_rows)
    cxc_vencida = sum(
        (r.valor_factura or 0) - (r.abonos or 0)
        for r in cxc_rows if r.fecha_vencimiento and r.fecha_vencimiento < hoy
    )
    cxp_pendiente = sum((r.valor or 0) - (r.abonos or 0) for r in cxp_rows)
    cxp_vencida = sum(
        (r.valor or 0) - (r.abonos or 0)
        for r in cxp_rows if r.fecha_vencimiento and r.fecha_vencimiento < hoy
    )

    total_cxc = await db.scalar(select(func.count(CuentaPorCobrar.id)).where(tenant_clause(CuentaPorCobrar)))
    total_cxp = await db.scalar(select(func.count(CuentaPorPagar.id)).where(tenant_clause(CuentaPorPagar)))

    return CarteraStats(
        total_cxc=total_cxc or 0,
        total_cxp=total_cxp or 0,
        cxc_pendiente=Decimal(str(cxc_pendiente)),
        cxc_vencida=Decimal(str(cxc_vencida)),
        cxp_pendiente=Decimal(str(cxp_pendiente)),
        cxp_vencida=Decimal(str(cxp_vencida)),
    )


# -- CxC -------------------------------------------------------

@router.get("/cartera/cxc", response_model=List[CxCResponse])
async def list_cxc(
    _: CurrentUser,
    estado: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = for_tenant(
        select(CuentaPorCobrar)
        .order_by(CuentaPorCobrar.fecha_vencimiento)
        .limit(limit)
        .offset(offset),
        CuentaPorCobrar,
    )
    if estado:
        q = q.where(CuentaPorCobrar.estado == estado)
    rows = (await db.execute(q)).scalars().all()
    return [_enrich_cxc(r) for r in rows]


@router.post("/cartera/cxc", response_model=CxCResponse, status_code=201)
async def create_cxc(body: CxCCreate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(
        select(CuentaPorCobrar).where(
            CuentaPorCobrar.numero_factura == body.numero_factura,
            tenant_clause(CuentaPorCobrar),
        )
    )
    if existing:
        raise HTTPException(400, "Ya existe una CxC con ese número de factura")
    cxc = CuentaPorCobrar(**body.model_dump())
    db.add(cxc)
    await db.commit()
    await db.refresh(cxc)
    return _enrich_cxc(cxc)


@router.put("/cartera/cxc/{cxc_id}", response_model=CxCResponse)
async def update_cxc(cxc_id: int, body: CxCUpdate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    cxc = await get_for_tenant(db, CuentaPorCobrar, cxc_id)
    if not cxc:
        raise HTTPException(404, "CxC no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cxc, field, value)
    await db.commit()
    await db.refresh(cxc)
    return _enrich_cxc(cxc)


@router.post("/cartera/cxc/{cxc_id}/abonar", response_model=AbonoCxCResultado)
async def abonar_cxc(
    cxc_id: int, body: AbonoCreate, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    # #12: bloquear la CxC para serializar abonos concurrentes (doble cobro).
    cxc = await db.scalar(
        select(CuentaPorCobrar)
        .where(CuentaPorCobrar.id == cxc_id, tenant_clause(CuentaPorCobrar))
        .with_for_update()
    )
    if not cxc:
        raise HTTPException(404, "CxC no encontrada")
    if cxc.estado in ("Pagado", "Anulado"):
        raise HTTPException(400, f"La CxC ya está en estado {cxc.estado}")
    saldo_anterior = (cxc.valor_factura or Decimal("0")) - (cxc.abonos or Decimal("0"))
    if body.valor > saldo_anterior:
        raise HTTPException(400, f"El abono (${body.valor}) supera el saldo pendiente (${saldo_anterior})")
    cxc.abonos = (cxc.abonos or Decimal("0")) + body.valor
    nuevo_saldo = cxc.valor_factura - cxc.abonos
    cxc.estado = EstadoDocumento.PAGADO if nuevo_saldo <= 0 else EstadoDocumento.PARCIAL
    if body.notas:
        cxc.notas = (cxc.notas or "") + f"\n[Abono ${body.valor}] {body.notas}"

    numero = await _next_numero_comprobante(db, "RC")
    pago = Pago(
        numero_comprobante=numero,
        tipo=TipoPago.CXC,
        cxc_id=cxc.id,
        valor=body.valor,
        saldo_anterior=saldo_anterior,
        saldo_nuevo=nuevo_saldo,
        notas=body.notas,
        usuario_id=current.id,
    )
    db.add(pago)
    await db.flush()

    # Asiento contable automático: DB Caja / CR Clientes
    await asiento_abono_cxc(db, pago, cxc, usuario_id=current.id)

    await db.commit()
    await db.refresh(cxc)
    await db.refresh(pago)
    return AbonoCxCResultado(
        documento=CxCResponse.model_validate(_enrich_cxc(cxc)),
        pago=PagoResponse.model_validate(pago),
    )


@router.patch("/cartera/cxc/{cxc_id}/anular", response_model=CxCResponse)
async def anular_cxc(cxc_id: int, _: ContableDep, db: AsyncSession = Depends(get_db)):
    cxc = await get_for_tenant(db, CuentaPorCobrar, cxc_id)
    if not cxc:
        raise HTTPException(404, "CxC no encontrada")
    cxc.estado = EstadoDocumento.ANULADO
    await db.commit()
    await db.refresh(cxc)
    return _enrich_cxc(cxc)


# -- CxP -------------------------------------------------------

@router.get("/cartera/cxp", response_model=List[CxPResponse])
async def list_cxp(
    _: CurrentUser,
    estado: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = for_tenant(
        select(CuentaPorPagar)
        .order_by(CuentaPorPagar.fecha_vencimiento)
        .limit(limit)
        .offset(offset),
        CuentaPorPagar,
    )
    if estado:
        q = q.where(CuentaPorPagar.estado == estado)
    rows = (await db.execute(q)).scalars().all()
    return [_enrich_cxp(r) for r in rows]


@router.post("/cartera/cxp", response_model=CxPResponse, status_code=201)
async def create_cxp(body: CxPCreate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(
        select(CuentaPorPagar).where(
            CuentaPorPagar.numero_documento == body.numero_documento,
            tenant_clause(CuentaPorPagar),
        )
    )
    if existing:
        raise HTTPException(400, "Ya existe una CxP con ese número de documento")
    cxp = CuentaPorPagar(**body.model_dump())
    db.add(cxp)
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)


@router.put("/cartera/cxp/{cxp_id}", response_model=CxPResponse)
async def update_cxp(cxp_id: int, body: CxPUpdate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    cxp = await get_for_tenant(db, CuentaPorPagar, cxp_id)
    if not cxp:
        raise HTTPException(404, "CxP no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cxp, field, value)
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)


@router.post("/cartera/cxp/{cxp_id}/abonar", response_model=AbonoCxPResultado)
async def abonar_cxp(
    cxp_id: int, body: AbonoCreate, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    # #12: bloquear la CxP para serializar abonos concurrentes (doble pago).
    cxp = await db.scalar(
        select(CuentaPorPagar)
        .where(CuentaPorPagar.id == cxp_id, tenant_clause(CuentaPorPagar))
        .with_for_update()
    )
    if not cxp:
        raise HTTPException(404, "CxP no encontrada")
    if cxp.estado in ("Pagado", "Anulado"):
        raise HTTPException(400, f"La CxP ya está en estado {cxp.estado}")
    saldo_anterior = (cxp.valor or Decimal("0")) - (cxp.abonos or Decimal("0"))
    if body.valor > saldo_anterior:
        raise HTTPException(400, f"El abono supera el saldo pendiente (${saldo_anterior})")
    cxp.abonos = (cxp.abonos or Decimal("0")) + body.valor
    nuevo_saldo = cxp.valor - cxp.abonos
    cxp.estado = EstadoDocumento.PAGADO if nuevo_saldo <= 0 else EstadoDocumento.PARCIAL
    if body.notas:
        cxp.notas = (cxp.notas or "") + f"\n[Abono ${body.valor}] {body.notas}"
    # Sincronizar estado_pago en la compra origen si existe
    if cxp.compra_id:
        compra = await get_for_tenant(db, CompraDocumento, cxp.compra_id)
        if compra and compra.estado != "Anulada":
            compra.estado_pago = "Pagado" if nuevo_saldo <= 0 else "Parcial"

    numero = await _next_numero_comprobante(db, "CE")
    pago = Pago(
        numero_comprobante=numero,
        tipo=TipoPago.CXP,
        cxp_id=cxp.id,
        valor=body.valor,
        saldo_anterior=saldo_anterior,
        saldo_nuevo=nuevo_saldo,
        notas=body.notas,
        usuario_id=current.id,
    )
    db.add(pago)
    await db.flush()

    # Asiento contable automático: DB Proveedores / CR Caja
    await asiento_abono_cxp(db, pago, cxp, usuario_id=current.id)

    await db.commit()
    await db.refresh(cxp)
    await db.refresh(pago)
    return AbonoCxPResultado(
        documento=CxPResponse.model_validate(_enrich_cxp(cxp)),
        pago=PagoResponse.model_validate(pago),
    )


@router.patch("/cartera/cxp/{cxp_id}/anular", response_model=CxPResponse)
async def anular_cxp(cxp_id: int, _: ContableDep, db: AsyncSession = Depends(get_db)):
    cxp = await get_for_tenant(db, CuentaPorPagar, cxp_id)
    if not cxp:
        raise HTTPException(404, "CxP no encontrada")
    cxp.estado = EstadoDocumento.ANULADO
    if cxp.compra_id:
        compra = await get_for_tenant(db, CompraDocumento, cxp.compra_id)
        if compra and compra.estado != "Anulada":
            compra.estado_pago = "Anulado"
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)


# -- Pagos (historial / reimpresión de comprobantes) -----------

@router.get("/cartera/pagos", response_model=List[PagoResponse])
async def list_pagos(
    _: CurrentUser,
    cxc_id: Optional[int] = Query(None),
    cxp_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = for_tenant(select(Pago).order_by(Pago.fecha.desc()), Pago)
    if cxc_id:
        q = q.where(Pago.cxc_id == cxc_id)
    if cxp_id:
        q = q.where(Pago.cxp_id == cxp_id)
    rows = (await db.execute(q)).scalars().all()
    return rows


@router.post("/cartera/pagos/{pago_id}/anular", response_model=PagoResponse)
async def anular_pago(
    pago_id: int, current: ContableDep, db: AsyncSession = Depends(get_db)
):
    """
    Anula un abono mal registrado: restaura el saldo y estado del documento
    (CxC/CxP), re-sincroniza el estado_pago de la compra si aplica, y genera
    el reverso del asiento contable. El comprobante queda marcado como anulado
    pero visible (trazabilidad). Bloqueado si el período contable está cerrado.
    """
    # #12: bloquear el pago y el documento de cartera antes de restaurar saldos.
    pago = await db.scalar(
        select(Pago).where(Pago.id == pago_id, tenant_clause(Pago)).with_for_update()
    )
    if not pago:
        raise HTTPException(404, "Comprobante de pago no encontrado")
    if pago.anulado:
        raise HTTPException(400, f"El comprobante {pago.numero_comprobante} ya está anulado")

    # Reverso contable primero: si el período está cerrado, lanza 400 y el
    # rollback deja todo intacto
    await reversar_asientos(
        db,
        documento_ref=pago.numero_comprobante,
        usuario_id=current.id,
        motivo=f"Anulación de abono {pago.numero_comprobante}",
    )

    # Restaurar saldo y estado del documento de cartera
    if pago.tipo == TipoPago.CXC and pago.cxc_id:
        cxc = await db.scalar(
            select(CuentaPorCobrar)
            .where(CuentaPorCobrar.id == pago.cxc_id, tenant_clause(CuentaPorCobrar))
            .with_for_update()
        )
        if cxc:
            cxc.abonos = max((cxc.abonos or Decimal("0")) - pago.valor, Decimal("0"))
            if cxc.estado != EstadoDocumento.ANULADO:
                cxc.estado = (
                    EstadoDocumento.PARCIAL if cxc.abonos > 0 else EstadoDocumento.PENDIENTE
                )
    elif pago.tipo == TipoPago.CXP and pago.cxp_id:
        cxp = await db.scalar(
            select(CuentaPorPagar)
            .where(CuentaPorPagar.id == pago.cxp_id, tenant_clause(CuentaPorPagar))
            .with_for_update()
        )
        if cxp:
            cxp.abonos = max((cxp.abonos or Decimal("0")) - pago.valor, Decimal("0"))
            if cxp.estado != EstadoDocumento.ANULADO:
                cxp.estado = (
                    EstadoDocumento.PARCIAL if cxp.abonos > 0 else EstadoDocumento.PENDIENTE
                )
            # Re-sincronizar la compra origen
            if cxp.compra_id:
                compra = await get_for_tenant(db, CompraDocumento, cxp.compra_id)
                if compra and compra.estado != "Anulada":
                    compra.estado_pago = "Parcial" if cxp.abonos > 0 else "Pendiente"

    pago.anulado = True
    pago.notas = ((pago.notas or "") + "\n[ANULADO] Reversado por correccion").strip()

    await db.commit()
    await db.refresh(pago)
    return pago


# ════════════════════════════════════════════════════════════
# ASIENTOS CONTABLES — consulta (partida doble)
# ════════════════════════════════════════════════════════════

def _asiento_response(a: AsientoContable, movimientos) -> AsientoResponse:
    movs = [
        MovimientoAsientoResponse(
            id=m.id,
            cuenta_id=m.cuenta_id,
            cuenta_codigo=m.cuenta.codigo_puc if m.cuenta else None,
            cuenta_nombre=m.cuenta.nombre if m.cuenta else None,
            centro_costo_id=m.centro_costo_id,
            debito=m.debito,
            credito=m.credito,
            descripcion=m.descripcion,
        )
        for m in movimientos
    ]
    return AsientoResponse(
        id=a.id,
        fecha=a.fecha,
        descripcion=a.descripcion,
        tipo_documento=a.tipo_documento,
        modulo_origen=a.modulo_origen,
        documento_ref=a.documento_ref,
        usuario_id=a.usuario_id,
        periodo_id=a.periodo_id,
        anulado=a.anulado,
        reversado=a.reversado,
        created_at=a.created_at,
        movimientos=movs,
        total_debito=sum((m.debito for m in movimientos), Decimal("0.00")),
        total_credito=sum((m.credito for m in movimientos), Decimal("0.00")),
    )


@router.get("/asientos", response_model=List[AsientoResponse])
async def list_asientos(
    _: ContableDep,
    modulo_origen: Optional[str] = Query(None),
    documento_ref: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Libro diario: asientos con sus movimientos (filtros por módulo y documento)."""
    q = for_tenant(
        select(AsientoContable)
        .options(selectinload(AsientoContable.movimientos).selectinload(MovimientoAsiento.cuenta))
        .order_by(AsientoContable.fecha.desc(), AsientoContable.id.desc()),
        AsientoContable,
    )
    if modulo_origen:
        q = q.where(AsientoContable.modulo_origen == modulo_origen)
    if documento_ref:
        q = q.where(AsientoContable.documento_ref == documento_ref)
    asientos = (await db.execute(q)).scalars().all()
    return [_asiento_response(a, a.movimientos) for a in asientos]


@router.get("/asientos/{asiento_id}", response_model=AsientoResponse)
async def get_asiento(asiento_id: int, _: ContableDep, db: AsyncSession = Depends(get_db)):
    asiento = await db.scalar(
        select(AsientoContable)
        .options(selectinload(AsientoContable.movimientos).selectinload(MovimientoAsiento.cuenta))
        .where(AsientoContable.id == asiento_id, tenant_clause(AsientoContable))
    )
    if not asiento:
        raise HTTPException(404, "Asiento no encontrado")
    return _asiento_response(asiento, asiento.movimientos)


@router.get("/terceros/{tercero_id}/auxiliar", response_model=AuxiliarTerceroResponse)
async def auxiliar_tercero(
    tercero_id: int,
    _: ContableDep,
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    cuenta: Optional[str] = Query(None, description="Filtrar por código PUC (ej. 130505)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Auxiliar contable / estado de cuenta del tercero: todos sus movimientos
    del libro diario con saldo acumulado (débitos − créditos). Para un cliente,
    el saldo del auxiliar de 130505 es lo que debe; para un proveedor en
    220501, el saldo negativo es lo que se le debe.
    """
    tercero = await get_for_tenant(db, Tercero, tercero_id)
    if not tercero:
        raise HTTPException(404, "Tercero no encontrado")

    q = (
        select(MovimientoAsiento, AsientoContable, PlanCuentas)
        .join(AsientoContable, AsientoContable.id == MovimientoAsiento.asiento_id)
        .join(PlanCuentas, PlanCuentas.id == MovimientoAsiento.cuenta_id)
        .where(MovimientoAsiento.tercero_id == tercero_id, tenant_clause(MovimientoAsiento))
        .order_by(AsientoContable.fecha, AsientoContable.id, MovimientoAsiento.id)
    )
    if fecha_desde:
        q = q.where(AsientoContable.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.where(AsientoContable.fecha <= fecha_hasta)
    if cuenta:
        q = q.where(PlanCuentas.codigo_puc == cuenta)

    movimientos: List[MovimientoAuxiliar] = []
    saldo = Decimal("0.00")
    total_deb = Decimal("0.00")
    total_cred = Decimal("0.00")
    for mov, asiento, cta in (await db.execute(q)).all():
        saldo += mov.debito - mov.credito
        total_deb += mov.debito
        total_cred += mov.credito
        movimientos.append(MovimientoAuxiliar(
            fecha=asiento.fecha,
            asiento_id=asiento.id,
            documento_ref=asiento.documento_ref,
            descripcion=asiento.descripcion,
            cuenta_codigo=cta.codigo_puc,
            cuenta_nombre=cta.nombre,
            debito=mov.debito,
            credito=mov.credito,
            saldo_acumulado=saldo,
        ))

    return AuxiliarTerceroResponse(
        tercero_id=tercero.id,
        nit_cc=tercero.nit_cc,
        razon_social=tercero.razon_social,
        tipo=tercero.tipo.value if hasattr(tercero.tipo, "value") else tercero.tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        movimientos=movimientos,
        total_debitos=total_deb,
        total_creditos=total_cred,
        saldo_final=saldo,
    )
