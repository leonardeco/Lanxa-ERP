from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.tenancy import TenantScoped
from app.core.time import utcnow


class Proveedor(TenantScoped, Base):
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nit_cc: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    dv: Mapped[str | None] = mapped_column(String(1))
    razon_social: Mapped[str] = mapped_column(String(200))
    nombre_comercial: Mapped[str | None] = mapped_column(String(200))
    tipo_persona: Mapped[str] = mapped_column(String(20), default="Jurídica")
    regimen_iva: Mapped[str] = mapped_column(String(50), default="Responsable")
    categoria: Mapped[str | None] = mapped_column(String(100))
    direccion: Mapped[str | None] = mapped_column(String(300))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    departamento: Mapped[str | None] = mapped_column(String(100))
    telefono: Mapped[str | None] = mapped_column(String(20))
    celular: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    contacto_nombre: Mapped[str | None] = mapped_column(String(100))
    contacto_cargo: Mapped[str | None] = mapped_column(String(100))
    dias_credito: Mapped[int] = mapped_column(default=30)
    activo: Mapped[bool] = mapped_column(default=True)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    compras = relationship("CompraDocumento", back_populates="proveedor")


class CompraDocumento(TenantScoped, Base):
    __tablename__ = "compras_documentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    fecha: Mapped[date] = mapped_column(Date)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedores.id"))
    proveedor_razon_social: Mapped[str | None] = mapped_column(String(200))
    proveedor_nit: Mapped[str | None] = mapped_column(String(20))
    ref_proveedor: Mapped[str | None] = mapped_column(String(100))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    descuento_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    base_gravable: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    iva_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    retefuente: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    reteiva: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    reteica: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    estado: Mapped[str] = mapped_column(String(20), default="Borrador")
    estado_pago: Mapped[str] = mapped_column(String(20), default="Pendiente")
    observaciones: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    proveedor = relationship("Proveedor", back_populates="compras")
    detalles = relationship("CompraDetalle", back_populates="compra", cascade="all, delete-orphan")


class CompraDetalle(TenantScoped, Base):
    __tablename__ = "compras_detalles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    compra_id: Mapped[int] = mapped_column(ForeignKey("compras_documentos.id"))
    producto_id: Mapped[int | None] = mapped_column(ForeignKey("productos.id"))
    descripcion: Mapped[str] = mapped_column(String(300))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("1.000"))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    descuento_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"))
    iva_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("19.00"))
    subtotal_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    iva_valor: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    # Lote + vencimiento del renglón (solo productos con controla_lote). Se llenan
    # en el borrador y alimentan el Lote que se crea al confirmar la compra.
    codigo_lote: Mapped[str | None] = mapped_column(String(60))
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    compra = relationship("CompraDocumento", back_populates="detalles")


class DevolucionCompra(TenantScoped, Base):
    """Devolución a proveedor — nota débito sobre una compra confirmada."""
    __tablename__ = "devoluciones_compra"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # ND-0001
    compra_id: Mapped[int] = mapped_column(ForeignKey("compras_documentos.id"), index=True)
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    motivo: Mapped[str] = mapped_column(String(300))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    iva_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    compra = relationship("CompraDocumento")
    detalles = relationship(
        "DevolucionCompraDetalle", back_populates="devolucion", cascade="all, delete-orphan")


class DevolucionCompraDetalle(TenantScoped, Base):
    __tablename__ = "devoluciones_compra_detalles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    devolucion_id: Mapped[int] = mapped_column(ForeignKey("devoluciones_compra.id"))
    compra_detalle_id: Mapped[int] = mapped_column(ForeignKey("compras_detalles.id"))
    producto_id: Mapped[int | None] = mapped_column(ForeignKey("productos.id"))
    descripcion: Mapped[str] = mapped_column(String(300))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    subtotal_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    iva_valor: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total_linea: Mapped[Decimal] = mapped_column(Numeric(18, 2))

    devolucion = relationship("DevolucionCompra", back_populates="detalles")
