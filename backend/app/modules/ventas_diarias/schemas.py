"""
Super Ozono Global — Schemas Pydantic para Ventas Diarias (Run 6)
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class VentaDiariaDetalleCreate(BaseModel):
    producto_id: int
    cantidad: Decimal = Field(default=Decimal("1.00"), gt=0)
    venta: Optional[Decimal] = Field(default=None, ge=0)
    abono_1: Optional[Decimal] = Field(default=None, ge=0)
    abono_2: Optional[Decimal] = Field(default=None, ge=0)
    pesos_c: Optional[Decimal] = None
    valor_flete: Optional[Decimal] = None


class VentaDiariaDetalleResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: Decimal
    venta: Optional[Decimal] = None
    abono_1: Optional[Decimal] = None
    abono_2: Optional[Decimal] = None
    saldo: Decimal
    pesos_c: Optional[Decimal] = None
    valor_flete: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class VentaDiariaCreate(BaseModel):
    fecha: date
    asesor: Optional[str] = Field(default=None, max_length=200)
    guia: Optional[str] = Field(default=None, max_length=50)
    codigo_guia: Optional[str] = Field(default=None, max_length=20)
    cliente_id: int
    estado: str = "Pendiente"
    forma_pago: Optional[str] = Field(default=None, max_length=100)
    notas: Optional[str] = None
    detalles: List[VentaDiariaDetalleCreate] = Field(min_length=1)


class VentaDiariaResponse(BaseModel):
    id: int
    fecha: date
    asesor: Optional[str] = None
    guia: Optional[str] = None
    codigo_guia: Optional[str] = None
    cliente_id: int
    estado: str
    forma_pago: Optional[str] = None
    notas: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    detalles: List[VentaDiariaDetalleResponse] = []

    model_config = {"from_attributes": True}


class VentaDiariaResumenMensual(BaseModel):
    anio: int
    mes: int
    total_venta: Decimal
    total_abonado: Decimal
    total_saldo: Decimal
    cantidad_entregado: int
    cantidad_devolucion: int


class PagoSueltoResponse(BaseModel):
    id: int
    fecha: date
    cliente_texto: str
    monto: Decimal
    revisado: bool
    notas: Optional[str] = None

    model_config = {"from_attributes": True}


class PagoSueltoUpdate(BaseModel):
    revisado: bool
