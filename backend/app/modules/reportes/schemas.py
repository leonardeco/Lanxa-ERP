from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import date


class AgingBucket(BaseModel):
    bucket: str
    cantidad: int
    total: Decimal


class AgingDetalle(BaseModel):
    id: int
    numero: str
    tercero: str
    nit: str
    saldo_pendiente: Decimal
    dias_vencido: int
    bucket: str
    fecha_vencimiento: Optional[date] = None


class AgingReporte(BaseModel):
    buckets: List[AgingBucket]
    detalle: List[AgingDetalle]
    total_pendiente: Decimal


class AgingCarteraResponse(BaseModel):
    cxc: AgingReporte
    cxp: AgingReporte


class TotalPorGrupo(BaseModel):
    nombre: str
    total: float
    cantidad: int


class ComprasPeriodoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total: Decimal
    cantidad_documentos: int
    por_proveedor: List[TotalPorGrupo]


class VentasPeriodoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    total: Decimal
    cantidad_documentos: int
    por_cliente: List[TotalPorGrupo]
    por_marca: List[TotalPorGrupo]


class RetencionesPeriodoResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    compras_retefuente: Decimal
    compras_reteiva: Decimal
    compras_reteica: Decimal
    ventas_retefuente: Decimal
    ventas_reteiva: Decimal
    ventas_reteica: Decimal
    total_retefuente: Decimal
    total_reteiva: Decimal
    total_reteica: Decimal


# ══════════════════════════════════════════════════════════
# Estados financieros — P&L y Balance General
# ══════════════════════════════════════════════════════════

class CuentaSaldo(BaseModel):
    codigo_puc: str
    nombre: str
    saldo: Decimal


class GrupoEstadoFinanciero(BaseModel):
    clase: str
    total: Decimal
    cuentas: List[CuentaSaldo]


class EstadoResultadosResponse(BaseModel):
    fecha_desde: date
    fecha_hasta: date
    ingresos: GrupoEstadoFinanciero
    costos: GrupoEstadoFinanciero
    gastos: GrupoEstadoFinanciero
    utilidad_bruta: Decimal      # ingresos - costos
    utilidad_neta: Decimal       # ingresos - costos - gastos


class BalanceGeneralResponse(BaseModel):
    fecha_corte: date
    activo: GrupoEstadoFinanciero
    pasivo: GrupoEstadoFinanciero
    patrimonio: GrupoEstadoFinanciero
    resultado_del_ejercicio: Decimal   # utilidad acumulada (va al patrimonio)
    total_activo: Decimal
    total_pasivo_patrimonio: Decimal   # pasivo + patrimonio + resultado
    cuadrado: bool                     # total_activo == total_pasivo_patrimonio
