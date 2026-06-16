"""
Super Ozono Global — Pydantic Schemas para la API REST
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


# ══════════════════════════════════════════════════════════
# Plan de Cuentas (PUC)
# ══════════════════════════════════════════════════════════

class PlanCuentasBase(BaseModel):
    codigo_puc: str = Field(..., max_length=20, description="Código PUC según Decreto 2650")
    nombre: str = Field(..., max_length=200)
    clase: str
    naturaleza: str
    nivel: str = "Auxiliar"
    requiere_tercero: bool = False
    requiere_centro_costo: bool = False
    activo: bool = True


class PlanCuentasResponse(PlanCuentasBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# Centros de Costo
# ══════════════════════════════════════════════════════════

class CentroCostoBase(BaseModel):
    codigo: str = Field(..., max_length=20)
    nombre: str = Field(..., max_length=100)
    tipo: str
    marca_asociada: Optional[str] = None
    responsable: Optional[str] = None
    activo: bool = True
    notas: Optional[str] = None


class CentroCostoResponse(CentroCostoBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# Períodos Contables
# ══════════════════════════════════════════════════════════

class PeriodoContableBase(BaseModel):
    anio: int
    mes: int
    periodo: str
    estado: str = "Abierto"
    notas: Optional[str] = None


class PeriodoContableResponse(PeriodoContableBase):
    id: int
    fecha_cierre: Optional[date] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# Terceros
# ══════════════════════════════════════════════════════════

class TerceroBase(BaseModel):
    nit_cc: str = Field(..., max_length=20)
    dv: Optional[str] = None
    razon_social: str = Field(..., max_length=200)
    tipo: str
    tipo_persona: Optional[str] = None
    regimen_iva: Optional[str] = None
    ciudad: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    activo: bool = True
    notas: Optional[str] = None


class TerceroResponse(TerceroBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# Parámetros Tributarios
# ══════════════════════════════════════════════════════════

class ParametroTributarioBase(BaseModel):
    concepto: str
    tarifa_valor: Optional[Decimal] = None
    base_aplica: Optional[str] = None
    cuenta_puc: Optional[str] = None
    notas: Optional[str] = None


class ParametroTributarioResponse(ParametroTributarioBase):
    id: int
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# Parámetros de Nómina
# ══════════════════════════════════════════════════════════

class ParametroNominaBase(BaseModel):
    concepto: str
    valor_porcentaje: Optional[Decimal] = None
    tipo: Optional[str] = None
    notas: Optional[str] = None


class ParametroNominaResponse(ParametroNominaBase):
    id: int
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# Dashboard Stats
# ══════════════════════════════════════════════════════════

class DashboardStats(BaseModel):
    total_cuentas_puc: int = 0
    total_centros_costo: int = 0
    total_periodos: int = 0
    total_terceros: int = 0
    total_parametros_tributarios: int = 0
    total_parametros_nomina: int = 0
    empresa_nit: str = ""
    empresa_razon_social: str = ""


# ══════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str = "ok"
    database: str = "connected"
    version: str = "0.1.0"
    empresa: str = "Super Ozono Global"
