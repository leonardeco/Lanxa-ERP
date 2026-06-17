"""
Super Ozono Global — API Routes (Contabilidad Núcleo)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import date
from decimal import Decimal

from app.core.database import get_db
from app.core.config import get_settings
from app.api.deps import CurrentUser, AdminOrAdministradoraDep
from app.modules.contabilidad.models import (
    PlanCuentas, CentroCosto, PeriodoContable, Tercero,
    ParametroTributario, ParametroNomina,
    CuentaPorCobrar, CuentaPorPagar, EstadoDocumento,
    Pago, TipoPago,
)
from app.modules.compras.models import CompraDocumento
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
)

router = APIRouter(prefix="/api/v1/contabilidad", tags=["Contabilidad"])
settings = get_settings()


# ── Dashboard Stats ──────────────────────────────────────

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(_: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Estadísticas generales del módulo contable."""
    cuentas = await db.scalar(select(func.count(PlanCuentas.id)))
    centros = await db.scalar(select(func.count(CentroCosto.id)))
    periodos = await db.scalar(select(func.count(PeriodoContable.id)))
    terceros = await db.scalar(select(func.count(Tercero.id)))
    tributarios = await db.scalar(select(func.count(ParametroTributario.id)))
    nomina = await db.scalar(select(func.count(ParametroNomina.id)))

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
async def list_plan_cuentas(_: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PlanCuentas).order_by(PlanCuentas.codigo_puc))
    return result.scalars().all()


@router.get("/puc/{codigo}", response_model=PlanCuentasResponse)
async def get_cuenta_puc(codigo: str, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PlanCuentas).where(PlanCuentas.codigo_puc == codigo))
    cuenta = result.scalar_one_or_none()
    if not cuenta:
        raise HTTPException(status_code=404, detail=f"Cuenta PUC {codigo} no encontrada")
    return cuenta


@router.post("/puc", response_model=PlanCuentasResponse, status_code=201)
async def create_cuenta_puc(body: PlanCuentasCreate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(PlanCuentas).where(PlanCuentas.codigo_puc == body.codigo_puc))
    if existing:
        raise HTTPException(400, f"Ya existe la cuenta PUC {body.codigo_puc}")
    cuenta = PlanCuentas(**body.model_dump())
    db.add(cuenta)
    await db.commit()
    await db.refresh(cuenta)
    return cuenta


@router.put("/puc/{cuenta_id}", response_model=PlanCuentasResponse)
async def update_cuenta_puc(cuenta_id: int, body: PlanCuentasUpdate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    cuenta = await db.get(PlanCuentas, cuenta_id)
    if not cuenta:
        raise HTTPException(404, "Cuenta PUC no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cuenta, field, value)
    await db.commit()
    await db.refresh(cuenta)
    return cuenta


@router.patch("/puc/{cuenta_id}/toggle", response_model=PlanCuentasResponse)
async def toggle_cuenta_puc(cuenta_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    cuenta = await db.get(PlanCuentas, cuenta_id)
    if not cuenta:
        raise HTTPException(404, "Cuenta PUC no encontrada")
    cuenta.activo = not cuenta.activo
    await db.commit()
    await db.refresh(cuenta)
    return cuenta


# ── Centros de Costo ─────────────────────────────────────

@router.get("/centros-costo", response_model=List[CentroCostoResponse])
async def list_centros_costo(_: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CentroCosto).order_by(CentroCosto.codigo))
    return result.scalars().all()


@router.post("/centros-costo", response_model=CentroCostoResponse, status_code=201)
async def create_centro_costo(body: CentroCostoCreate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(CentroCosto).where(CentroCosto.codigo == body.codigo))
    if existing:
        raise HTTPException(400, f"Ya existe el centro de costo {body.codigo}")
    cc = CentroCosto(**body.model_dump())
    db.add(cc)
    await db.commit()
    await db.refresh(cc)
    return cc


@router.put("/centros-costo/{cc_id}", response_model=CentroCostoResponse)
async def update_centro_costo(cc_id: int, body: CentroCostoUpdate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    cc = await db.get(CentroCosto, cc_id)
    if not cc:
        raise HTTPException(404, "Centro de costo no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cc, field, value)
    await db.commit()
    await db.refresh(cc)
    return cc


@router.patch("/centros-costo/{cc_id}/toggle", response_model=CentroCostoResponse)
async def toggle_centro_costo(cc_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    cc = await db.get(CentroCosto, cc_id)
    if not cc:
        raise HTTPException(404, "Centro de costo no encontrado")
    cc.activo = not cc.activo
    await db.commit()
    await db.refresh(cc)
    return cc


# ── Períodos Contables ───────────────────────────────────

@router.get("/periodos", response_model=List[PeriodoContableResponse])
async def list_periodos(_: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PeriodoContable).order_by(PeriodoContable.anio, PeriodoContable.mes)
    )
    return result.scalars().all()


@router.post("/periodos", response_model=PeriodoContableResponse, status_code=201)
async def create_periodo(body: PeriodoContableCreate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    periodo_str = f"{body.anio}-{body.mes:02d}"
    existing = await db.scalar(select(PeriodoContable).where(PeriodoContable.periodo == periodo_str))
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
async def toggle_periodo(periodo_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    periodo = await db.get(PeriodoContable, periodo_id)
    if not periodo:
        raise HTTPException(404, "Período no encontrado")
    if periodo.estado == EstadoPeriodo.ABIERTO:
        periodo.estado = EstadoPeriodo.CERRADO
        periodo.fecha_cierre = date.today()
    else:
        periodo.estado = EstadoPeriodo.ABIERTO
        periodo.fecha_cierre = None
    await db.commit()
    await db.refresh(periodo)
    return periodo


# ── Terceros ─────────────────────────────────────────────

@router.get("/terceros", response_model=List[TerceroResponse])
async def list_terceros(_: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    """Listar todos los terceros registrados."""
    result = await db.execute(
        select(Tercero).order_by(Tercero.razon_social)
    )
    return result.scalars().all()


# ── Parámetros Tributarios ───────────────────────────────

@router.get("/parametros-tributarios", response_model=List[ParametroTributarioResponse])
async def list_parametros_tributarios(
    _: AdminOrAdministradoraDep,
    activo: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(ParametroTributario).order_by(ParametroTributario.concepto)
    if activo is not None:
        q = q.where(ParametroTributario.activo == activo)
    return (await db.execute(q)).scalars().all()


@router.put("/parametros-tributarios/{param_id}", response_model=ParametroTributarioResponse)
async def update_parametro_tributario(param_id: int, body: ParametroTributarioUpdate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    param = await db.get(ParametroTributario, param_id)
    if not param:
        raise HTTPException(404, "Parámetro tributario no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(param, field, value)
    await db.commit()
    await db.refresh(param)
    return param


@router.patch("/parametros-tributarios/{param_id}/toggle", response_model=ParametroTributarioResponse)
async def toggle_parametro_tributario(param_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    param = await db.get(ParametroTributario, param_id)
    if not param:
        raise HTTPException(404, "Parámetro tributario no encontrado")
    param.activo = not param.activo
    await db.commit()
    await db.refresh(param)
    return param


# ── Parámetros de Nómina ─────────────────────────────────

@router.get("/parametros-nomina", response_model=List[ParametroNominaResponse])
async def list_parametros_nomina(
    _: AdminOrAdministradoraDep,
    activo: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(ParametroNomina).order_by(ParametroNomina.concepto)
    if activo is not None:
        q = q.where(ParametroNomina.activo == activo)
    return (await db.execute(q)).scalars().all()


@router.put("/parametros-nomina/{param_id}", response_model=ParametroNominaResponse)
async def update_parametro_nomina(param_id: int, body: ParametroNominaUpdate, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    param = await db.get(ParametroNomina, param_id)
    if not param:
        raise HTTPException(404, "Parámetro de nómina no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(param, field, value)
    await db.commit()
    await db.refresh(param)
    return param


@router.patch("/parametros-nomina/{param_id}/toggle", response_model=ParametroNominaResponse)
async def toggle_parametro_nomina(param_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    param = await db.get(ParametroNomina, param_id)
    if not param:
        raise HTTPException(404, "Parámetro de nómina no encontrado")
    param.activo = not param.activo
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
    nums = (await db.execute(
        select(Pago.numero_comprobante).where(Pago.numero_comprobante.like(f"{prefijo}-%"))
    )).scalars().all()
    max_num = max((int(n.split("-")[-1]) for n in nums), default=0)
    return f"{prefijo}-{max_num + 1:04d}"


def _enrich_cxc(c: CuentaPorCobrar) -> dict:
    saldo = (c.valor_factura or Decimal("0")) - (c.abonos or Decimal("0"))
    return {**c.__dict__, "saldo_pendiente": saldo, "dias_vencido": _dias_vencido(c.fecha_vencimiento, c.estado)}


def _enrich_cxp(p: CuentaPorPagar) -> dict:
    saldo = (p.valor or Decimal("0")) - (p.abonos or Decimal("0"))
    return {**p.__dict__, "saldo_pendiente": saldo, "dias_vencido": _dias_vencido(p.fecha_vencimiento, p.estado), "compra_id": p.compra_id}


# -- Stats globales de cartera ---------------------------------

@router.get("/cartera/stats", response_model=CarteraStats)
async def cartera_stats(_: CurrentUser, db: AsyncSession = Depends(get_db)):
    hoy = date.today()

    cxc_rows = (await db.execute(
        select(CuentaPorCobrar).where(CuentaPorCobrar.estado.notin_(["Pagado", "Anulado"]))
    )).scalars().all()
    cxp_rows = (await db.execute(
        select(CuentaPorPagar).where(CuentaPorPagar.estado.notin_(["Pagado", "Anulado"]))
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

    total_cxc = await db.scalar(select(func.count(CuentaPorCobrar.id)))
    total_cxp = await db.scalar(select(func.count(CuentaPorPagar.id)))

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
    db: AsyncSession = Depends(get_db),
):
    q = select(CuentaPorCobrar).order_by(CuentaPorCobrar.fecha_vencimiento)
    if estado:
        q = q.where(CuentaPorCobrar.estado == estado)
    rows = (await db.execute(q)).scalars().all()
    return [_enrich_cxc(r) for r in rows]


@router.post("/cartera/cxc", response_model=CxCResponse, status_code=201)
async def create_cxc(body: CxCCreate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(CuentaPorCobrar).where(CuentaPorCobrar.numero_factura == body.numero_factura))
    if existing:
        raise HTTPException(400, "Ya existe una CxC con ese número de factura")
    cxc = CuentaPorCobrar(**body.model_dump())
    db.add(cxc)
    await db.commit()
    await db.refresh(cxc)
    return _enrich_cxc(cxc)


@router.put("/cartera/cxc/{cxc_id}", response_model=CxCResponse)
async def update_cxc(cxc_id: int, body: CxCUpdate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    cxc = await db.get(CuentaPorCobrar, cxc_id)
    if not cxc:
        raise HTTPException(404, "CxC no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cxc, field, value)
    await db.commit()
    await db.refresh(cxc)
    return _enrich_cxc(cxc)


@router.post("/cartera/cxc/{cxc_id}/abonar", response_model=AbonoCxCResultado)
async def abonar_cxc(cxc_id: int, body: AbonoCreate, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    cxc = await db.get(CuentaPorCobrar, cxc_id)
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

    await db.commit()
    await db.refresh(cxc)
    await db.refresh(pago)
    return AbonoCxCResultado(documento=_enrich_cxc(cxc), pago=pago)


@router.patch("/cartera/cxc/{cxc_id}/anular", response_model=CxCResponse)
async def anular_cxc(cxc_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    cxc = await db.get(CuentaPorCobrar, cxc_id)
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
    db: AsyncSession = Depends(get_db),
):
    q = select(CuentaPorPagar).order_by(CuentaPorPagar.fecha_vencimiento)
    if estado:
        q = q.where(CuentaPorPagar.estado == estado)
    rows = (await db.execute(q)).scalars().all()
    return [_enrich_cxp(r) for r in rows]


@router.post("/cartera/cxp", response_model=CxPResponse, status_code=201)
async def create_cxp(body: CxPCreate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(CuentaPorPagar).where(CuentaPorPagar.numero_documento == body.numero_documento))
    if existing:
        raise HTTPException(400, "Ya existe una CxP con ese número de documento")
    cxp = CuentaPorPagar(**body.model_dump())
    db.add(cxp)
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)


@router.put("/cartera/cxp/{cxp_id}", response_model=CxPResponse)
async def update_cxp(cxp_id: int, body: CxPUpdate, _: CurrentUser, db: AsyncSession = Depends(get_db)):
    cxp = await db.get(CuentaPorPagar, cxp_id)
    if not cxp:
        raise HTTPException(404, "CxP no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cxp, field, value)
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)


@router.post("/cartera/cxp/{cxp_id}/abonar", response_model=AbonoCxPResultado)
async def abonar_cxp(cxp_id: int, body: AbonoCreate, current: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    cxp = await db.get(CuentaPorPagar, cxp_id)
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
        compra = await db.get(CompraDocumento, cxp.compra_id)
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

    await db.commit()
    await db.refresh(cxp)
    await db.refresh(pago)
    return AbonoCxPResultado(documento=_enrich_cxp(cxp), pago=pago)


@router.patch("/cartera/cxp/{cxp_id}/anular", response_model=CxPResponse)
async def anular_cxp(cxp_id: int, _: AdminOrAdministradoraDep, db: AsyncSession = Depends(get_db)):
    cxp = await db.get(CuentaPorPagar, cxp_id)
    if not cxp:
        raise HTTPException(404, "CxP no encontrada")
    cxp.estado = EstadoDocumento.ANULADO
    if cxp.compra_id:
        compra = await db.get(CompraDocumento, cxp.compra_id)
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
    q = select(Pago).order_by(Pago.fecha.desc())
    if cxc_id:
        q = q.where(Pago.cxc_id == cxc_id)
    if cxp_id:
        q = q.where(Pago.cxp_id == cxp_id)
    rows = (await db.execute(q)).scalars().all()
    return rows
