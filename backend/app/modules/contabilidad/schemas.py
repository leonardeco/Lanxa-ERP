"""
Super Ozono Global — Pydantic Schemas para la API REST
"""

from pydantic import BaseModel, Field
from typing import List, Optional
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


class PlanCuentasCreate(PlanCuentasBase):
    pass


class PlanCuentasUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None
    requiere_tercero: Optional[bool] = None
    requiere_centro_costo: Optional[bool] = None


class PlanCuentasResponse(PlanCuentasBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


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


class CentroCostoCreate(CentroCostoBase):
    pass


class CentroCostoUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    marca_asociada: Optional[str] = None
    responsable: Optional[str] = None
    activo: Optional[bool] = None
    notas: Optional[str] = None


class CentroCostoResponse(CentroCostoBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# Períodos Contables
# ══════════════════════════════════════════════════════════

class PeriodoContableBase(BaseModel):
    anio: int
    mes: int
    periodo: str
    estado: str = "Abierto"
    notas: Optional[str] = None


class PeriodoContableCreate(BaseModel):
    anio: int
    mes: int


class PeriodoContableResponse(PeriodoContableBase):
    id: int
    fecha_cierre: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


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

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# Parámetros Tributarios
# ══════════════════════════════════════════════════════════

class ParametroTributarioBase(BaseModel):
    concepto: str
    tarifa_valor: Optional[Decimal] = None
    base_aplica: Optional[str] = None
    cuenta_puc: Optional[str] = None
    notas: Optional[str] = None


class ParametroTributarioUpdate(BaseModel):
    tarifa_valor: Optional[Decimal] = None
    base_aplica: Optional[str] = None
    cuenta_puc: Optional[str] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


class ParametroTributarioResponse(ParametroTributarioBase):
    id: int
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# Parámetros de Nómina
# ══════════════════════════════════════════════════════════

class ParametroNominaBase(BaseModel):
    concepto: str
    valor_porcentaje: Optional[Decimal] = None
    tipo: Optional[str] = None
    notas: Optional[str] = None


class ParametroNominaUpdate(BaseModel):
    valor_porcentaje: Optional[Decimal] = None
    tipo: Optional[str] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


class ParametroNominaResponse(ParametroNominaBase):
    id: int
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


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
# Cuentas por Cobrar (CxC)
# ══════════════════════════════════════════════════════════

class CxCCreate(BaseModel):
    numero_factura: str
    fecha_emision: date
    cliente_nit: str
    nombre_cliente: str
    marca: Optional[str] = None
    valor_factura: Decimal = Field(gt=0)
    fecha_vencimiento: Optional[date] = None
    notas: Optional[str] = None


class CxCUpdate(BaseModel):
    nombre_cliente: Optional[str] = None
    marca: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    notas: Optional[str] = None


class AbonoCreate(BaseModel):
    valor: Decimal = Field(gt=0, description="Valor del abono; debe ser mayor que cero")
    notas: Optional[str] = None


class CxCResponse(BaseModel):
    id: int
    numero_factura: str
    fecha_emision: date
    cliente_nit: str
    nombre_cliente: Optional[str]
    marca: Optional[str]
    valor_factura: Decimal
    abonos: Decimal
    saldo_pendiente: Optional[Decimal]
    fecha_vencimiento: Optional[date]
    estado: str
    dias_vencido: int = 0
    notas: Optional[str]
    created_at: Optional[datetime] = None  # nullable en el modelo (default utcnow)

    model_config = {"from_attributes": True}


class CarteraStats(BaseModel):
    total_cxc: int = 0
    total_cxp: int = 0
    cxc_pendiente: Decimal = Decimal("0")
    cxc_vencida: Decimal = Decimal("0")
    cxp_pendiente: Decimal = Decimal("0")
    cxp_vencida: Decimal = Decimal("0")


# ══════════════════════════════════════════════════════════
# Cuentas por Pagar (CxP)
# ══════════════════════════════════════════════════════════

class CxPCreate(BaseModel):
    numero_documento: str
    fecha: date
    proveedor_nit: str
    razon_social: str
    concepto: Optional[str] = None
    valor: Decimal = Field(gt=0)
    fecha_vencimiento: Optional[date] = None
    notas: Optional[str] = None


class CxPUpdate(BaseModel):
    razon_social: Optional[str] = None
    concepto: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    notas: Optional[str] = None


class CxPResponse(BaseModel):
    id: int
    numero_documento: str
    fecha: date
    proveedor_nit: str
    razon_social: Optional[str]
    concepto: Optional[str]
    valor: Decimal
    abonos: Decimal
    saldo_pendiente: Optional[Decimal]
    fecha_vencimiento: Optional[date]
    estado: str
    dias_vencido: int = 0
    compra_id: Optional[int] = None
    notas: Optional[str]
    created_at: Optional[datetime] = None  # nullable en el modelo (default utcnow)

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# Comprobantes de pago (Recibo de Caja / Comprobante de Egreso)
# ══════════════════════════════════════════════════════════

class PagoResponse(BaseModel):
    id: int
    numero_comprobante: str
    tipo: str
    cxc_id: Optional[int] = None
    cxp_id: Optional[int] = None
    valor: Decimal
    saldo_anterior: Decimal
    saldo_nuevo: Decimal
    notas: Optional[str] = None
    usuario_id: Optional[int] = None
    fecha: datetime
    anulado: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class AbonoCxCResultado(BaseModel):
    documento: CxCResponse
    pago: PagoResponse


class AbonoCxPResultado(BaseModel):
    documento: CxPResponse
    pago: PagoResponse


# ══════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str = "ok"
    database: str = "connected"
    version: str = "0.1.0"
    empresa: str = "Super Ozono Global"


# ══════════════════════════════════════════════════════════
# Asientos contables (partida doble)
# ══════════════════════════════════════════════════════════

class MovimientoAsientoResponse(BaseModel):
    id: int
    cuenta_id: int
    cuenta_codigo: Optional[str] = None
    cuenta_nombre: Optional[str] = None
    centro_costo_id: Optional[int] = None
    debito: Decimal
    credito: Decimal
    descripcion: Optional[str] = None

    model_config = {"from_attributes": True}


class AsientoResponse(BaseModel):
    id: int
    fecha: date
    descripcion: str
    tipo_documento: Optional[str] = None
    modulo_origen: Optional[str] = None
    documento_ref: Optional[str] = None
    usuario_id: Optional[int] = None
    periodo_id: Optional[int] = None
    anulado: bool
    reversado: bool
    created_at: Optional[datetime] = None
    movimientos: List[MovimientoAsientoResponse] = []
    total_debito: Decimal = Decimal("0.00")
    total_credito: Decimal = Decimal("0.00")


class MovimientoAuxiliar(BaseModel):
    fecha: date
    asiento_id: int
    documento_ref: Optional[str] = None
    descripcion: str
    cuenta_codigo: str
    cuenta_nombre: str
    debito: Decimal
    credito: Decimal
    saldo_acumulado: Decimal  # débitos - créditos corrido (naturaleza cliente)


class AuxiliarTerceroResponse(BaseModel):
    tercero_id: int
    nit_cc: str
    razon_social: str
    tipo: str
    fecha_desde: Optional[date] = None
    fecha_hasta: Optional[date] = None
    movimientos: List[MovimientoAuxiliar]
    total_debitos: Decimal
    total_creditos: Decimal
    saldo_final: Decimal
