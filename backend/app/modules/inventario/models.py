"""
Super Ozono Global — Módulo de Inventario: Modelos SQLAlchemy
Kardex de movimientos de stock, generado automáticamente desde Compras y Ventas
o registrado manualmente como ajuste.
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Numeric, ForeignKey, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.tenancy import TenantScoped
from app.core.time import bogota_now, utcnow
import enum


class TipoMovimientoInventario(str, enum.Enum):
    ENTRADA = "Entrada"
    SALIDA = "Salida"
    AJUSTE_POSITIVO = "Ajuste positivo"
    AJUSTE_NEGATIVO = "Ajuste negativo"


class OrigenMovimiento(str, enum.Enum):
    COMPRA = "Compra"
    VENTA = "Venta"
    AJUSTE_MANUAL = "Ajuste manual"
    REVERSO_COMPRA = "Reverso de compra"
    REVERSO_VENTA = "Reverso de venta"
    DEVOLUCION_VENTA = "Devolución venta"
    DEVOLUCION_COMPRA = "Devolución compra"


class MovimientoInventario(TenantScoped, Base):
    """Kardex — un registro por cada movimiento de stock, con snapshot antes/después."""
    __tablename__ = "movimientos_inventario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), index=True)
    tipo: Mapped[TipoMovimientoInventario] = mapped_column(SAEnum(TipoMovimientoInventario))
    origen: Mapped[OrigenMovimiento] = mapped_column(SAEnum(OrigenMovimiento))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    stock_antes: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    stock_despues: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

    # FK lógicas (sin constraint real) — mismo patrón que CuentaPorPagar.compra_id
    compra_id: Mapped[int | None] = mapped_column(index=True)
    compra_detalle_id: Mapped[int | None] = mapped_column()
    venta_id: Mapped[int | None] = mapped_column(index=True)
    venta_detalle_id: Mapped[int | None] = mapped_column()
    # Lote afectado (solo productos con controla_lote) — trazabilidad del kardex
    lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id"), index=True)

    motivo: Mapped[str | None] = mapped_column(String(300))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    # Fecha de negocio del movimiento, en hora local de Colombia
    fecha: Mapped[datetime] = mapped_column(DateTime, default=bogota_now)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    producto = relationship("Producto")


class Lote(TenantScoped, Base):
    """Un lote de un producto con control de vencimiento (controla_lote=True).

    El stock del producto (stock_actual) es el agregado = Σ cantidad_actual de sus
    lotes activos. Las salidas consumen por FEFO (vencimiento más próximo primero).
    """
    __tablename__ = "lotes"
    __table_args__ = (
        UniqueConstraint("producto_id", "codigo_lote", name="uq_lote_producto_codigo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), index=True)
    codigo_lote: Mapped[str] = mapped_column(String(60))
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, index=True)
    cantidad_actual: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    cantidad_inicial: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    origen: Mapped[str | None] = mapped_column(String(40))  # Compra / Importación / Ajuste
    fecha_ingreso: Mapped[datetime] = mapped_column(DateTime, default=bogota_now)
    activo: Mapped[bool] = mapped_column(default=True)

    producto = relationship("Producto")

    def __repr__(self):
        return f"<Lote {self.codigo_lote} prod#{self.producto_id} x{self.cantidad_actual}>"
