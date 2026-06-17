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
