"""
Super Ozono Global — Módulo de Ventas & Comercial: Modelos SQLAlchemy
Productos, Clientes, Documentos de Venta y Detalles de Venta
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    Numeric, ForeignKey, Text, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(30), unique=True, nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    categoria = Column(SAEnum(CategoriaProducto), default=CategoriaProducto.BIOCIDA)
    marca = Column(String(100), nullable=False)  # Nombre de marca (Superozono, Ecoozono, etc.)
    centro_costo_id = Column(Integer, ForeignKey("centros_costo.id"), nullable=True)
    unidad_medida = Column(SAEnum(UnidadMedida), default=UnidadMedida.LITRO)
    contenido_neto = Column(String(50), nullable=True)  # Ej: "1L", "20L", "200L"
    precio_venta = Column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    precio_costo = Column(Numeric(18, 2), nullable=True, default=Decimal("0.00"))
    tarifa_iva = Column(Numeric(5, 2), default=Decimal("19.00"))  # % IVA (19%, 5%, 0%)
    stock_actual = Column(Integer, default=0)
    stock_minimo = Column(Integer, default=5)
    activo = Column(Boolean, default=True)
    alegra_id = Column(Integer, nullable=True, index=True)
    registro_ica = Column(String(50), nullable=True)  # Registro ICA (para biocidas)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    centro_costo = relationship("CentroCosto")
    detalles_venta = relationship("VentaDetalle", back_populates="producto")

    def __repr__(self):
        return f"<Producto {self.sku} - {self.nombre}>"


class Cliente(Base):
    """Clientes comerciales — Distribuidores y compradores B2B"""
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nit_cc = Column(String(20), unique=True, nullable=False, index=True)
    dv = Column(String(1), nullable=True)
    razon_social = Column(String(200), nullable=False)
    nombre_comercial = Column(String(200), nullable=True)
    tipo_persona = Column(String(20), default="Jurídica")  # Natural / Jurídica
    regimen_iva = Column(String(50), default="Responsable")
    direccion = Column(String(300), nullable=True)
    ciudad = Column(String(100), nullable=True)
    departamento = Column(String(100), nullable=True)
    telefono = Column(String(30), nullable=True)
    celular = Column(String(30), nullable=True)
    email = Column(String(150), nullable=True)
    contacto_nombre = Column(String(200), nullable=True)  # Persona de contacto
    contacto_cargo = Column(String(100), nullable=True)
    lista_precios = Column(String(50), default="General")  # General, Distribuidor, Mayorista
    cupo_credito = Column(Numeric(18, 2), default=Decimal("0.00"))
    dias_credito = Column(Integer, default=30)
    activo = Column(Boolean, default=True)
    alegra_id = Column(Integer, nullable=True, index=True)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ventas = relationship("VentaDocumento", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente {self.nit_cc} - {self.razon_social}>"


class VentaDocumento(Base):
    """Documentos de venta — Cabecera de facturas internas"""
    __tablename__ = "ventas_documentos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(20), unique=True, nullable=False, index=True)  # SOG-V-0001
    fecha = Column(Date, nullable=False, default=date.today)
    fecha_vencimiento = Column(Date, nullable=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    centro_costo_id = Column(Integer, ForeignKey("centros_costo.id"), nullable=True)
    vendedor = Column(String(200), nullable=True)

    # Totales
    subtotal = Column(Numeric(18, 2), default=Decimal("0.00"))
    descuento_total = Column(Numeric(18, 2), default=Decimal("0.00"))
    base_gravable = Column(Numeric(18, 2), default=Decimal("0.00"))
    iva_total = Column(Numeric(18, 2), default=Decimal("0.00"))
    retefuente = Column(Numeric(18, 2), default=Decimal("0.00"))
    reteiva = Column(Numeric(18, 2), default=Decimal("0.00"))
    reteica = Column(Numeric(18, 2), default=Decimal("0.00"))
    total = Column(Numeric(18, 2), default=Decimal("0.00"))

    # Estado
    estado = Column(SAEnum(EstadoVenta), default=EstadoVenta.BORRADOR)
    estado_pago = Column(SAEnum(EstadoPago), default=EstadoPago.PENDIENTE)

    # Alegra (facturación electrónica)
    alegra_id = Column(Integer, nullable=True, index=True)
    alegra_numero = Column(String(50), nullable=True)
    cufe = Column(String(200), nullable=True)

    observaciones = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cliente = relationship("Cliente", back_populates="ventas")
    centro_costo = relationship("CentroCosto")
    detalles = relationship("VentaDetalle", back_populates="venta", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VentaDocumento {self.numero} - {self.total}>"


class VentaDetalle(Base):
    """Líneas de detalle de cada venta — Partida doble con productos"""
    __tablename__ = "ventas_detalles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    venta_id = Column(Integer, ForeignKey("ventas_documentos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    cantidad = Column(Numeric(12, 2), nullable=False, default=Decimal("1.00"))
    precio_unitario = Column(Numeric(18, 2), nullable=False)
    descuento_porcentaje = Column(Numeric(5, 2), default=Decimal("0.00"))
    subtotal_linea = Column(Numeric(18, 2), default=Decimal("0.00"))
    iva_porcentaje = Column(Numeric(5, 2), default=Decimal("19.00"))
    iva_valor = Column(Numeric(18, 2), default=Decimal("0.00"))
    total_linea = Column(Numeric(18, 2), default=Decimal("0.00"))
    notas = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    venta = relationship("VentaDocumento", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")

    def __repr__(self):
        return f"<VentaDetalle Prod:{self.producto_id} Cant:{self.cantidad} Total:{self.total_linea}>"
