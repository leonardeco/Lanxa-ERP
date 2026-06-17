from pydantic import BaseModel
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
    pass


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
    email: Optional[str] = None
    contacto_nombre: Optional[str] = None
    contacto_cargo: Optional[str] = None
    dias_credito: Optional[int] = None
    notas: Optional[str] = None


class ProveedorResponse(ProveedorBase):
    id: int
    activo: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CompraDetalleInput(BaseModel):
    descripcion: str
    producto_id: Optional[int] = None
    cantidad: Decimal = Decimal("1")
    precio_unitario: Decimal
    descuento_porcentaje: Decimal = Decimal("0")
    iva_porcentaje: Decimal = Decimal("19")


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
    created_at: datetime

    model_config = {"from_attributes": True}


class CompraInput(BaseModel):
    fecha: date
    fecha_vencimiento: Optional[date] = None
    proveedor_id: int
    ref_proveedor: Optional[str] = None
    retefuente: Decimal = Decimal("0")
    reteiva: Decimal = Decimal("0")
    reteica: Decimal = Decimal("0")
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
