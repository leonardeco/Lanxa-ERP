"""
Super Ozono Global — API Routes (Contabilidad Núcleo)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.core.database import get_db
from app.core.config import get_settings
from app.modules.contabilidad.models import (
    PlanCuentas, CentroCosto, PeriodoContable, Tercero,
    ParametroTributario, ParametroNomina,
)
from app.modules.contabilidad.schemas import (
    PlanCuentasResponse, CentroCostoResponse,
    PeriodoContableResponse, TerceroResponse,
    ParametroTributarioResponse, ParametroNominaResponse,
    DashboardStats,
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
