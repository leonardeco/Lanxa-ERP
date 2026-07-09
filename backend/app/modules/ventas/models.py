"""
Super Ozono Global — Módulo de Ventas & Comercial: Modelos SQLAlchemy
Productos, Clientes, Documentos de Venta y Detalles de Venta
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    String, Date, DateTime, Numeric, ForeignKey, Text, Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.time import utcnow
import enum


# ══════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════

class UnidadMedida(str, enum.Enum):
    LITRO = "Litro"
    GALON = "Galón"
    KILO = "Kilo"
    UNIDAD = "Unidad"
    CAJA = "Caja"
    CANECA = "Caneca"


class EstadoVenta(str, enum.Enum):
    BORRADOR = "Borrador"
    CONFIRMADA = "Confirmada"
    FACTURADA = "Facturada"
    ANULADA = "Anulada"


class EstadoPago(str, enum.Enum):
    PENDIENTE = "Pendiente"
    PARCIAL = "Parcial"
    PAGADO = "Pagado"


class EstadoCotizacion(str, enum.Enum):
    BORRADOR = "Borrador"
    ENVIADA = "Enviada"
    APROBADA = "Aprobada"
    RECHAZADA = "Rechazada"
    CONVERTIDA = "Convertida"


class CategoriaProducto(str, enum.Enum):
    BIOCIDA = "Biocida"
    FERTILIZANTE = "Fertilizante"
    COADYUVANTE = "Coadyuvante"
    DESINFECTANTE = "Desinfectante"
    OTRO = "Otro"


# ══════════════════════════════════════════════════════════
# MODELOS
# ══════════════════════════════════════════════════════════

class Producto(Base):
    """Catálogo de productos — Biocidas y agroquímicos por marca"""
    __tablename__ = "productos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[CategoriaProducto] = mapped_column(
        SAEnum(CategoriaProducto), default=CategoriaProducto.BIOCIDA)
    marca: Mapped[str] = mapped_column(String(100))  # Nombre de marca (Superozono, Ecoozono, etc.)
    centro_costo_id: Mapped[int | None] = mapped_column(ForeignKey("centros_costo.id"))
    unidad_medida: Mapped[UnidadMedida] = mapped_column(
        SAEnum(UnidadMedida), default=UnidadMedida.LITRO)
    contenido_neto: Mapped[str | None] = mapped_column(String(50))  # Ej: "1L", "20L", "200L"
    precio_venta: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    precio_costo: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    tarifa_iva: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("19.00"))  # % IVA (19%, 5%, 0%)
    stock_actual: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), default=Decimal("0"))  # admite cantidades fraccionarias (litros/galones)
    stock_minimo: Mapped[int] = mapped_column(default=5)
    # Trazabilidad por lote + vencimiento (opt-in). Los perecederos/orgánicos lo
    # activan; los durables (generadores) siguen con stock simple.
    controla_lote: Mapped[bool] = mapped_column(default=False)
    activo: Mapped[bool] = mapped_column(default=True)
    alegra_id: Mapped[int | None] = mapped_column(index=True)
    registro_ica: Mapped[str | None] = mapped_column(String(50))  # Registro ICA (para biocidas)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    centro_costo = relationship("CentroCosto")
    detalles_venta = relationship("VentaDetalle", back_populates="producto")

    def __repr__(self):
        return f"<Producto {self.sku} - {self.nombre}>"


class Cliente(Base):
    """Clientes comerciales — Distribuidores y compradores B2B"""
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nit_cc: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    dv: Mapped[str | None] = mapped_column(String(1))
    razon_social: Mapped[str] = mapped_column(String(200))
    nombre_comercial: Mapped[str | None] = mapped_column(String(200))
    tipo_persona: Mapped[str] = mapped_column(String(20), default="Jurídica")  # Natural / Jurídica
    regimen_iva: Mapped[str] = mapped_column(String(50), default="Responsable")
    direccion: Mapped[str | None] = mapped_column(String(300))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    departamento: Mapped[str | None] = mapped_column(String(100))
    telefono: Mapped[str | None] = mapped_column(String(30))
    celular: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150))
    contacto_nombre: Mapped[str | None] = mapped_column(String(200))  # Persona de contacto
    contacto_cargo: Mapped[str | None] = mapped_column(String(100))
    lista_precios: Mapped[str] = mapped_column(
        String(50), default="General")  # General, Distribuidor, Mayorista
    cupo_credito: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    dias_credito: Mapped[int] = mapped_column(default=30)
    # Perfil tributario del comprador — determina qué retenciones practica
    retiene_fuente: Mapped[bool] = mapped_column(default=False)
    retiene_iva: Mapped[bool] = mapped_column(default=False)
    retiene_ica: Mapped[bool] = mapped_column(default=False)
    tarifa_reteica: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))  # por mil (ej. 4.140)
    activo: Mapped[bool] = mapped_column(default=True)
    alegra_id: Mapped[int | None] = mapped_column(index=True)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    ventas = relationship("VentaDocumento", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente {self.nit_cc} - {self.razon_social}>"


class VentaDocumento(Base):
    """Documentos de venta — Cabecera de facturas internas"""
    __tablename__ = "ventas_documentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # SOG-V-0001
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    centro_costo_id: Mapped[int | None] = mapped_column(ForeignKey("centros_costo.id"))
    vendedor: Mapped[str | None] = mapped_column(String(200))

    # Totales
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    descuento_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    base_gravable: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    iva_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    retefuente: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    reteiva: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    reteica: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    # Estado
    estado: Mapped[EstadoVenta] = mapped_column(SAEnum(EstadoVenta), default=EstadoVenta.BORRADOR)
    estado_pago: Mapped[EstadoPago] = mapped_column(
        SAEnum(EstadoPago), default=EstadoPago.PENDIENTE)

    # Alegra (facturación electrónica)
    alegra_id: Mapped[int | None] = mapped_column(index=True)
    alegra_numero: Mapped[str | None] = mapped_column(String(50))
    cufe: Mapped[str | None] = mapped_column(String(200))

    observaciones: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    cliente = relationship("Cliente", back_populates="ventas")
    centro_costo = relationship("CentroCosto")
    detalles = relationship("VentaDetalle", back_populates="venta", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VentaDocumento {self.numero} - {self.total}>"


class VentaDetalle(Base):
    """Líneas de detalle de cada venta — Partida doble con productos"""
    __tablename__ = "ventas_detalles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas_documentos.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1.00"))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    descuento_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    subtotal_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("19.00"))
    iva_valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    notas: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    # Relationships
    venta = relationship("VentaDocumento", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")

    def __repr__(self):
        return f"<VentaDetalle Prod:{self.producto_id} Cant:{self.cantidad} Total:{self.total_linea}>"


class Cotizacion(Base):
    """Cotización comercial — COT-####. Sin efectos de inventario ni
    contabilidad: solo al convertirla nace una venta (en Borrador)."""
    __tablename__ = "cotizaciones"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # COT-0001
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    vigencia_dias: Mapped[int] = mapped_column(default=15)
    fecha_vencimiento: Mapped[date] = mapped_column(Date)  # fecha + vigencia_dias
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    vendedor: Mapped[str | None] = mapped_column(String(200))

    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    descuento_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    base_gravable: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    iva_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    estado: Mapped[EstadoCotizacion] = mapped_column(
        SAEnum(EstadoCotizacion), default=EstadoCotizacion.BORRADOR)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(300))
    venta_id: Mapped[int | None] = mapped_column(
        ForeignKey("ventas_documentos.id"), index=True)  # venta creada al convertir

    observaciones: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    cliente = relationship("Cliente")
    venta = relationship("VentaDocumento")
    detalles = relationship(
        "CotizacionDetalle", back_populates="cotizacion", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Cotizacion {self.numero} - {self.total}>"


class CotizacionDetalle(Base):
    __tablename__ = "cotizaciones_detalles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cotizacion_id: Mapped[int] = mapped_column(ForeignKey("cotizaciones.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1.00"))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    descuento_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    subtotal_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("19.00"))
    iva_valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    notas: Mapped[str | None] = mapped_column(String(300))

    cotizacion = relationship("Cotizacion", back_populates="detalles")
    producto = relationship("Producto")

    def __repr__(self):
        return f"<CotizacionDetalle Prod:{self.producto_id} Cant:{self.cantidad}>"


class DevolucionVenta(Base):
    """Nota crédito — devolución parcial o total de una venta confirmada."""
    __tablename__ = "devoluciones_venta"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # NC-0001
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas_documentos.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    motivo: Mapped[str] = mapped_column(String(300))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    iva_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    venta = relationship("VentaDocumento")
    detalles = relationship(
        "DevolucionVentaDetalle", back_populates="devolucion", cascade="all, delete-orphan")


class DevolucionVentaDetalle(Base):
    __tablename__ = "devoluciones_venta_detalles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    devolucion_id: Mapped[int] = mapped_column(ForeignKey("devoluciones_venta.id"))
    venta_detalle_id: Mapped[int] = mapped_column(ForeignKey("ventas_detalles.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    subtotal_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    iva_valor: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    devolucion = relationship("DevolucionVenta", back_populates="detalles")
