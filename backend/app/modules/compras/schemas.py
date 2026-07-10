from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.nit import validar_dv
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime


class ProveedorBase(BaseModel):
    nit_cc: str
    dv: Optional[str] = None
    razon_social: str
    nombre_comercial: Optional[str] = None
    tipo_persona: str = "Jurídica"
    regimen_iva: str = "Responsable"
    categoria: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    contacto_nombre: Optional[str] = None
    contacto_cargo: Optional[str] = None
    dias_credito: int = 30
    notas: Optional[str] = None


class ProveedorCreate(ProveedorBase):
    # 13a: formato de email validado solo en escritura (el Response queda como
    # str para no romper la lectura de registros legacy con texto libre)
    email: Optional[EmailStr] = None

    @field_validator("email", mode="before")
    @classmethod
    def _email_vacio_es_none(cls, v):
        return v or None

    @model_validator(mode="after")
    def _dv_correcto(self):
        error = validar_dv(self.nit_cc, self.dv)
        if error:
            raise ValueError(error)
        return self


class ProveedorUpdate(BaseModel):
    razon_social: Optional[str] = None
    nombre_comercial: Optional[str] = None
    tipo_persona: Optional[str] = None
    regimen_iva: Optional[str] = None
    categoria: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[EmailStr] = None
    contacto_nombre: Optional[str] = None
    contacto_cargo: Optional[str] = None
    dias_credito: Optional[int] = None
    notas: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def _email_vacio_es_none(cls, v):
        return v or None


class ProveedorResponse(ProveedorBase):
    id: int
    activo: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CompraDetalleInput(BaseModel):
    descripcion: str
    producto_id: Optional[int] = None
    cantidad: Decimal = Field(default=Decimal("1"), gt=0)
    precio_unitario: Decimal = Field(ge=0)
    descuento_porcentaje: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    iva_porcentaje: Decimal = Field(default=Decimal("19"), ge=0, le=100)
    # Trazabilidad por lote (solo productos con controla_lote). Se captura en el
    # borrador y se materializa como Lote al confirmar la compra.
    codigo_lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None


class CompraDetalleResponse(BaseModel):
    id: int
    compra_id: int
    producto_id: Optional[int] = None
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    descuento_porcentaje: Decimal
    iva_porcentaje: Decimal
    subtotal_linea: Decimal
    iva_valor: Decimal
    total_linea: Decimal
    codigo_lote: Optional[str] = None
    fecha_vencimiento: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CompraInput(BaseModel):
    fecha: date
    fecha_vencimiento: Optional[date] = None
    proveedor_id: int
    ref_proveedor: Optional[str] = None
    retefuente: Decimal = Field(default=Decimal("0"), ge=0)
    reteiva: Decimal = Field(default=Decimal("0"), ge=0)
    reteica: Decimal = Field(default=Decimal("0"), ge=0)
    observaciones: Optional[str] = None
    detalles: List[CompraDetalleInput]


class CompraResponse(BaseModel):
    id: int
    numero: str
    fecha: date
    fecha_vencimiento: Optional[date] = None
    proveedor_id: int
    proveedor_razon_social: Optional[str] = None
    proveedor_nit: Optional[str] = None
    ref_proveedor: Optional[str] = None
    subtotal: Decimal
    descuento_total: Decimal
    base_gravable: Decimal
    iva_total: Decimal
    retefuente: Decimal
    reteiva: Decimal
    reteica: Decimal
    total: Decimal
    estado: str
    estado_pago: str
    observaciones: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    detalles: List[CompraDetalleResponse] = []

    model_config = {"from_attributes": True}


class TopProveedor(BaseModel):
    proveedor: Optional[str]
    total: float


class ComprasDashboard(BaseModel):
    total_compras_mes: Decimal
    total_compras_mes_anterior: Decimal
    cantidad_compras_mes: int
    total_proveedores_activos: int
    cxp_pendiente: Decimal
    top_proveedores: List[TopProveedor]


# ── Devoluciones a proveedor (ND-####) ───────────────────

class DevolucionCompraDetalleInput(BaseModel):
    compra_detalle_id: int
    cantidad: Decimal = Field(gt=0)


class DevolucionCompraCreate(BaseModel):
    fecha: Optional[date] = None
    motivo: str = Field(min_length=3, max_length=300)
    detalles: List[DevolucionCompraDetalleInput] = Field(min_length=1)


class DevolucionCompraDetalleResponse(BaseModel):
    id: int
    compra_detalle_id: int
    producto_id: Optional[int] = None
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    subtotal_linea: Decimal
    iva_valor: Decimal
    total_linea: Decimal

    model_config = {"from_attributes": True}


class DevolucionCompraResponse(BaseModel):
    id: int
    numero: str
    compra_id: int
    fecha: date
    motivo: str
    subtotal: Decimal
    iva_total: Decimal
    total: Decimal
    created_at: Optional[datetime] = None
    detalles: List[DevolucionCompraDetalleResponse] = []

    model_config = {"from_attributes": True}
