from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nit_cc = Column(String(20), unique=True, nullable=False, index=True)
    dv = Column(String(1), nullable=True)
    razon_social = Column(String(200), nullable=False)
    nombre_comercial = Column(String(200), nullable=True)
    tipo_persona = Column(String(20), default="Jurídica")
    regimen_iva = Column(String(50), default="Responsable")
    categoria = Column(String(100), nullable=True)
    direccion = Column(String(300), nullable=True)
    ciudad = Column(String(100), nullable=True)
    departamento = Column(String(100), nullable=True)
    telefono = Column(String(20), nullable=True)
    celular = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    contacto_nombre = Column(String(100), nullable=True)
    contacto_cargo = Column(String(100), nullable=True)
    dias_credito = Column(Integer, default=30)
    activo = Column(Boolean, default=True)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    compras = relationship("CompraDocumento", back_populates="proveedor")


class CompraDocumento(Base):
    __tablename__ = "compras_documentos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(20), unique=True, nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    proveedor_razon_social = Column(String(200), nullable=True)
    proveedor_nit = Column(String(20), nullable=True)
    ref_proveedor = Column(String(100), nullable=True)
    subtotal = Column(Numeric(18, 2), default=Decimal("0.00"))
    descuento_total = Column(Numeric(18, 2), default=Decimal("0.00"))
    base_gravable = Column(Numeric(18, 2), default=Decimal("0.00"))
    iva_total = Column(Numeric(18, 2), default=Decimal("0.00"))
    retefuente = Column(Numeric(18, 2), default=Decimal("0.00"))
    reteiva = Column(Numeric(18, 2), default=Decimal("0.00"))
    reteica = Column(Numeric(18, 2), default=Decimal("0.00"))
    total = Column(Numeric(18, 2), default=Decimal("0.00"))
    estado = Column(String(20), default="Borrador")
    estado_pago = Column(String(20), default="Pendiente")
    observaciones = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    proveedor = relationship("Proveedor", back_populates="compras")
    detalles = relationship("CompraDetalle", back_populates="compra", cascade="all, delete-orphan")


class CompraDetalle(Base):
    __tablename__ = "compras_detalles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    compra_id = Column(Integer, ForeignKey("compras_documentos.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)
    descripcion = Column(String(300), nullable=False)
    cantidad = Column(Numeric(12, 3), default=Decimal("1.000"))
    precio_unitario = Column(Numeric(18, 2), nullable=False)
    descuento_porcentaje = Column(Numeric(5, 2), default=Decimal("0.00"))
    iva_porcentaje = Column(Numeric(5, 2), default=Decimal("19.00"))
    subtotal_linea = Column(Numeric(18, 2), default=Decimal("0.00"))
    iva_valor = Column(Numeric(18, 2), default=Decimal("0.00"))
    total_linea = Column(Numeric(18, 2), default=Decimal("0.00"))
    created_at = Column(DateTime, default=datetime.utcnow)

    compra = relationship("CompraDocumento", back_populates="detalles")
