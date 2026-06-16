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
from app.modules.contabilidad.models import (
    PlanCuentas, CentroCosto, PeriodoContable, Tercero,
    ParametroTributario, ParametroNomina,
    CuentaPorCobrar, CuentaPorPagar, EstadoDocumento,
)
from app.modules.contabilidad.schemas import (
    PlanCuentasResponse, CentroCostoResponse,
    PeriodoContableResponse, TerceroResponse,
    ParametroTributarioResponse, ParametroNominaResponse,
    DashboardStats,
    CxCCreate, CxCUpdate, CxCResponse, AbonoCreate,
    CxPCreate, CxPUpdate, CxPResponse, CarteraStats,
)

router = APIRouter(prefix="/api/v1/contabilidad", tags=["Contabilidad"])
settings = get_settings()


# ── Dashboard Stats ──────────────────────────────────────

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
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
async def list_plan_cuentas(db: AsyncSession = Depends(get_db)):
    """Listar todas las cuentas del PUC."""
    result = await db.execute(
        select(PlanCuentas).order_by(PlanCuentas.codigo_puc)
    )
    return result.scalars().all()


@router.get("/puc/{codigo}", response_model=PlanCuentasResponse)
async def get_cuenta_puc(codigo: str, db: AsyncSession = Depends(get_db)):
    """Obtener una cuenta PUC por código."""
    result = await db.execute(
        select(PlanCuentas).where(PlanCuentas.codigo_puc == codigo)
    )
    cuenta = result.scalar_one_or_none()
    if not cuenta:
        raise HTTPException(status_code=404, detail=f"Cuenta PUC {codigo} no encontrada")
    return cuenta


# ── Centros de Costo ─────────────────────────────────────

@router.get("/centros-costo", response_model=List[CentroCostoResponse])
async def list_centros_costo(db: AsyncSession = Depends(get_db)):
    """Listar todos los centros de costo (marcas y áreas)."""
    result = await db.execute(
        select(CentroCosto).order_by(CentroCosto.codigo)
    )
    return result.scalars().all()


# ── Períodos Contables ───────────────────────────────────

@router.get("/periodos", response_model=List[PeriodoContableResponse])
async def list_periodos(db: AsyncSession = Depends(get_db)):
    """Listar todos los períodos contables."""
    result = await db.execute(
        select(PeriodoContable).order_by(PeriodoContable.anio, PeriodoContable.mes)
    )
    return result.scalars().all()


# ── Terceros ─────────────────────────────────────────────

@router.get("/terceros", response_model=List[TerceroResponse])
async def list_terceros(db: AsyncSession = Depends(get_db)):
    """Listar todos los terceros registrados."""
    result = await db.execute(
        select(Tercero).order_by(Tercero.razon_social)
    )
    return result.scalars().all()


# ── Parámetros Tributarios ───────────────────────────────

@router.get("/parametros-tributarios", response_model=List[ParametroTributarioResponse])
async def list_parametros_tributarios(db: AsyncSession = Depends(get_db)):
    """Listar parámetros tributarios vigentes."""
    result = await db.execute(
        select(ParametroTributario).where(ParametroTributario.activo == True)
        .order_by(ParametroTributario.concepto)
    )
    return result.scalars().all()


# ── Parámetros de Nómina ─────────────────────────────────

@router.get("/parametros-nomina", response_model=List[ParametroNominaResponse])
async def list_parametros_nomina(db: AsyncSession = Depends(get_db)):
    """Listar parámetros de nómina vigentes."""
    result = await db.execute(
        select(ParametroNomina).where(ParametroNomina.activo == True)
        .order_by(ParametroNomina.concepto)
    )
    return result.scalars().all()


# ════════════════════════════════════════════════════════════
# CARTERA — Cuentas por Cobrar y por Pagar
# ════════════════════════════════════════════════════════════

def _dias_vencido(fecha_vencimiento, estado: str) -> int:
    if not fecha_vencimiento or estado in ("Pagado", "Anulado"):
        return 0
    delta = (date.today() - fecha_vencimiento).days
    return max(delta, 0)


def _enrich_cxc(c: CuentaPorCobrar) -> dict:
    saldo = (c.valor_factura or Decimal("0")) - (c.abonos or Decimal("0"))
    return {**c.__dict__, "saldo_pendiente": saldo, "dias_vencido": _dias_vencido(c.fecha_vencimiento, c.estado)}


def _enrich_cxp(p: CuentaPorPagar) -> dict:
    saldo = (p.valor or Decimal("0")) - (p.abonos or Decimal("0"))
    return {**p.__dict__, "saldo_pendiente": saldo, "dias_vencido": _dias_vencido(p.fecha_vencimiento, p.estado)}


# -- Stats globales de cartera ---------------------------------

@router.get("/cartera/stats", response_model=CarteraStats)
async def cartera_stats(db: AsyncSession = Depends(get_db)):
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
    estado: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(CuentaPorCobrar).order_by(CuentaPorCobrar.fecha_vencimiento)
    if estado:
        q = q.where(CuentaPorCobrar.estado == estado)
    rows = (await db.execute(q)).scalars().all()
    return [_enrich_cxc(r) for r in rows]


@router.post("/cartera/cxc", response_model=CxCResponse, status_code=201)
async def create_cxc(body: CxCCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(CuentaPorCobrar).where(CuentaPorCobrar.numero_factura == body.numero_factura))
    if existing:
        raise HTTPException(400, "Ya existe una CxC con ese número de factura")
    cxc = CuentaPorCobrar(**body.model_dump())
    db.add(cxc)
    await db.commit()
    await db.refresh(cxc)
    return _enrich_cxc(cxc)


@router.put("/cartera/cxc/{cxc_id}", response_model=CxCResponse)
async def update_cxc(cxc_id: int, body: CxCUpdate, db: AsyncSession = Depends(get_db)):
    cxc = await db.get(CuentaPorCobrar, cxc_id)
    if not cxc:
        raise HTTPException(404, "CxC no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cxc, field, value)
    await db.commit()
    await db.refresh(cxc)
    return _enrich_cxc(cxc)


@router.post("/cartera/cxc/{cxc_id}/abonar", response_model=CxCResponse)
async def abonar_cxc(cxc_id: int, body: AbonoCreate, db: AsyncSession = Depends(get_db)):
    cxc = await db.get(CuentaPorCobrar, cxc_id)
    if not cxc:
        raise HTTPException(404, "CxC no encontrada")
    if cxc.estado in ("Pagado", "Anulado"):
        raise HTTPException(400, f"La CxC ya está en estado {cxc.estado}")
    saldo = (cxc.valor_factura or Decimal("0")) - (cxc.abonos or Decimal("0"))
    if body.valor > saldo:
        raise HTTPException(400, f"El abono (${body.valor}) supera el saldo pendiente (${saldo})")
    cxc.abonos = (cxc.abonos or Decimal("0")) + body.valor
    nuevo_saldo = cxc.valor_factura - cxc.abonos
    cxc.estado = EstadoDocumento.PAGADO if nuevo_saldo <= 0 else EstadoDocumento.PARCIAL
    if body.notas:
        cxc.notas = (cxc.notas or "") + f"\n[Abono ${body.valor}] {body.notas}"
    await db.commit()
    await db.refresh(cxc)
    return _enrich_cxc(cxc)


@router.patch("/cartera/cxc/{cxc_id}/anular", response_model=CxCResponse)
async def anular_cxc(cxc_id: int, db: AsyncSession = Depends(get_db)):
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
    estado: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(CuentaPorPagar).order_by(CuentaPorPagar.fecha_vencimiento)
    if estado:
        q = q.where(CuentaPorPagar.estado == estado)
    rows = (await db.execute(q)).scalars().all()
    return [_enrich_cxp(r) for r in rows]


@router.post("/cartera/cxp", response_model=CxPResponse, status_code=201)
async def create_cxp(body: CxPCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(CuentaPorPagar).where(CuentaPorPagar.numero_documento == body.numero_documento))
    if existing:
        raise HTTPException(400, "Ya existe una CxP con ese número de documento")
    cxp = CuentaPorPagar(**body.model_dump())
    db.add(cxp)
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)


@router.put("/cartera/cxp/{cxp_id}", response_model=CxPResponse)
async def update_cxp(cxp_id: int, body: CxPUpdate, db: AsyncSession = Depends(get_db)):
    cxp = await db.get(CuentaPorPagar, cxp_id)
    if not cxp:
        raise HTTPException(404, "CxP no encontrada")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(cxp, field, value)
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)


@router.post("/cartera/cxp/{cxp_id}/abonar", response_model=CxPResponse)
async def abonar_cxp(cxp_id: int, body: AbonoCreate, db: AsyncSession = Depends(get_db)):
    cxp = await db.get(CuentaPorPagar, cxp_id)
    if not cxp:
        raise HTTPException(404, "CxP no encontrada")
    if cxp.estado in ("Pagado", "Anulado"):
        raise HTTPException(400, f"La CxP ya está en estado {cxp.estado}")
    saldo = (cxp.valor or Decimal("0")) - (cxp.abonos or Decimal("0"))
    if body.valor > saldo:
        raise HTTPException(400, f"El abono supera el saldo pendiente (${saldo})")
    cxp.abonos = (cxp.abonos or Decimal("0")) + body.valor
    nuevo_saldo = cxp.valor - cxp.abonos
    cxp.estado = EstadoDocumento.PAGADO if nuevo_saldo <= 0 else EstadoDocumento.PARCIAL
    if body.notas:
        cxp.notas = (cxp.notas or "") + f"\n[Abono ${body.valor}] {body.notas}"
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)


@router.patch("/cartera/cxp/{cxp_id}/anular", response_model=CxPResponse)
async def anular_cxp(cxp_id: int, db: AsyncSession = Depends(get_db)):
    cxp = await db.get(CuentaPorPagar, cxp_id)
    if not cxp:
        raise HTTPException(404, "CxP no encontrada")
    cxp.estado = EstadoDocumento.ANULADO
    await db.commit()
    await db.refresh(cxp)
    return _enrich_cxp(cxp)
