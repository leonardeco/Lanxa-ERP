"""
Super Ozono Global — Schemas Pydantic para Ventas & Comercial
"""

from pydantic import BaseModel, Field, field_serializer, model_validator

from app.core.nit import validar_dv
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# ══════════════════════════════════════════════════════════
# Productos
# ══════════════════════════════════════════════════════════

class ProductoBase(BaseModel):
    sku: str = Field(..., max_length=30)
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    categoria: str = "Biocida"
    marca: str = Field(..., max_length=100)
    centro_costo_id: Optional[int] = None
    unidad_medida: str = "Litro"
    contenido_neto: Optional[str] = None
    precio_venta: Decimal = Field(default=Decimal("0.00"), ge=0)
    precio_costo: Optional[Decimal] = Field(default=Decimal("0.00"), ge=0)
    tarifa_iva: Decimal = Field(default=Decimal("19.00"), ge=0, le=100)
    stock_actual: Decimal = Decimal("0")  # admite fraccionarios; se serializa como número
    stock_minimo: int = 5
    activo: bool = True
    registro_ica: Optional[str] = None
    notas: Optional[str] = None

    @field_serializer("stock_actual")
    def _serialize_stock_actual(self, v: Decimal) -> float:
        """Emite el stock como número JSON (no string) para no romper el frontend."""
        return float(v)


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    categoria: Optional[str] = None
    marca: Optional[str] = None
    centro_costo_id: Optional[int] = None
    unidad_medida: Optional[str] = None
    contenido_neto: Optional[str] = None
    precio_venta: Optional[Decimal] = None
    precio_costo: Optional[Decimal] = None
    tarifa_iva: Optional[Decimal] = None
    stock_actual: Optional[int] = None
    stock_minimo: Optional[int] = None
    activo: Optional[bool] = None
    registro_ica: Optional[str] = None
    notas: Optional[str] = None


class ProductoResponse(ProductoBase):
    id: int
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# Clientes
# ══════════════════════════════════════════════════════════

class ClienteBase(BaseModel):
    nit_cc: str = Field(..., max_length=20)
    dv: Optional[str] = None
    razon_social: str = Field(..., max_length=200)
    nombre_comercial: Optional[str] = None
    tipo_persona: str = "Jurídica"
    regimen_iva: str = "Responsable"
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    contacto_nombre: Optional[str] = None
    contacto_cargo: Optional[str] = None
    lista_precios: str = "General"
    cupo_credito: Decimal = Decimal("0.00")
    dias_credito: int = 30
    # Perfil tributario del comprador
    retiene_fuente: bool = False
    retiene_iva: bool = False
    retiene_ica: bool = False
    tarifa_reteica: Optional[Decimal] = None  # por mil (ej. 4.140)
    activo: bool = True
    notas: Optional[str] = None


class ClienteCreate(ClienteBase):
    @model_validator(mode="after")
    def _dv_correcto(self):
        # 14e: si el usuario digita el DV, debe ser el correcto según la DIAN
        error = validar_dv(self.nit_cc, self.dv)
        if error:
            raise ValueError(error)
        return self


class ClienteUpdate(BaseModel):
    razon_social: Optional[str] = None
    nombre_comercial: Optional[str] = None
    tipo_persona: Optional[str] = None
    regimen_iva: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    departamento: Optional[str] = None
    telefono: Optional[str] = None
    celular: Optional[str] = None
    email: Optional[str] = None
    contacto_nombre: Optional[str] = None
    contacto_cargo: Optional[str] = None
    lista_precios: Optional[str] = None
    cupo_credito: Optional[Decimal] = None
    dias_credito: Optional[int] = None
    retiene_fuente: Optional[bool] = None
    retiene_iva: Optional[bool] = None
    retiene_ica: Optional[bool] = None
    tarifa_reteica: Optional[Decimal] = None
    activo: Optional[bool] = None
    notas: Optional[str] = None


class ClienteResponse(ClienteBase):
    id: int
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# Ventas — Detalles
# ══════════════════════════════════════════════════════════

class VentaDetalleCreate(BaseModel):
    producto_id: int
    cantidad: Decimal = Field(default=Decimal("1.00"), gt=0)
    precio_unitario: Decimal = Field(ge=0)
    descuento_porcentaje: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    iva_porcentaje: Decimal = Field(default=Decimal("19.00"), ge=0, le=100)
    notas: Optional[str] = None


class VentaDetalleResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: Decimal
    precio_unitario: Decimal
    descuento_porcentaje: Decimal
    subtotal_linea: Decimal
    iva_porcentaje: Decimal
    iva_valor: Decimal
    total_linea: Decimal
    notas: Optional[str] = None
    created_at: datetime | None = None

    # Producto info for display
    producto_nombre: Optional[str] = None
    producto_sku: Optional[str] = None

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# Ventas — Documento
# ══════════════════════════════════════════════════════════

class VentaCreate(BaseModel):
    fecha: date
    fecha_vencimiento: Optional[date] = None
    cliente_id: int
    centro_costo_id: Optional[int] = None
    vendedor: Optional[str] = None
    observaciones: Optional[str] = None
    detalles: List[VentaDetalleCreate] = []
    # Override manual de retenciones (opcional). Si se omite, se sugieren según
    # el perfil tributario del cliente y los ParametroTributario vigentes.
    retefuente: Optional[Decimal] = Field(default=None, ge=0)
    reteiva: Optional[Decimal] = Field(default=None, ge=0)
    reteica: Optional[Decimal] = Field(default=None, ge=0)


class VentaResponse(BaseModel):
    id: int
    numero: str
    fecha: date
    fecha_vencimiento: Optional[date] = None
    cliente_id: int
    centro_costo_id: Optional[int] = None
    vendedor: Optional[str] = None
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
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    # Related data for display
    cliente_razon_social: Optional[str] = None
    cliente_nit: Optional[str] = None
    detalles: List[VentaDetalleResponse] = []

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# Dashboard de Ventas
# ══════════════════════════════════════════════════════════

class VentaDashboardStats(BaseModel):
    ventas_mes_actual: Decimal = Decimal("0.00")
    ventas_mes_anterior: Decimal = Decimal("0.00")
    cantidad_ventas_mes: int = 0
    total_clientes_activos: int = 0
    total_productos_activos: int = 0
    ticket_promedio: Decimal = Decimal("0.00")
    productos_stock_bajo: int = 0
    ventas_por_marca: List[dict] = []


# ══════════════════════════════════════════════════════════
# Devoluciones (Nota crédito)
# ══════════════════════════════════════════════════════════

class DevolucionDetalleInput(BaseModel):
    venta_detalle_id: int
    cantidad: Decimal = Field(gt=0)


class DevolucionCreate(BaseModel):
    fecha: Optional[date] = None  # default: hoy
    motivo: str = Field(min_length=3, max_length=300)
    detalles: List[DevolucionDetalleInput] = Field(min_length=1)


class DevolucionDetalleResponse(BaseModel):
    id: int
    venta_detalle_id: int
    producto_id: int
    cantidad: Decimal
    precio_unitario: Decimal
    subtotal_linea: Decimal
    iva_valor: Decimal
    total_linea: Decimal

    model_config = {"from_attributes": True}


class DevolucionResponse(BaseModel):
    id: int
    numero: str
    venta_id: int
    fecha: date
    motivo: str
    subtotal: Decimal
    iva_total: Decimal
    total: Decimal
    created_at: datetime | None = None
    detalles: List[DevolucionDetalleResponse] = []

    model_config = {"from_attributes": True}
