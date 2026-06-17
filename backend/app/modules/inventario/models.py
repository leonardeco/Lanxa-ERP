"""
Super Ozono Global — Módulo de Inventario: Modelos SQLAlchemy
Kardex de movimientos de stock, generado automáticamente desde Compras y Ventas
o registrado manualmente como ajuste.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
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


class MovimientoInventario(Base):
    """Kardex — un registro por cada movimiento de stock, con snapshot antes/después."""
    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    tipo = Column(SAEnum(TipoMovimientoInventario), nullable=False)
    origen = Column(SAEnum(OrigenMovimiento), nullable=False)
    cantidad = Column(Numeric(12, 3), nullable=False)
    stock_antes = Column(Integer, nullable=False)
    stock_despues = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(18, 2), nullable=True)

    # FK lógicas (sin constraint real) — mismo patrón que CuentaPorPagar.compra_id
    compra_id = Column(Integer, nullable=True, index=True)
    compra_detalle_id = Column(Integer, nullable=True)
    venta_id = Column(Integer, nullable=True, index=True)
    venta_detalle_id = Column(Integer, nullable=True)

    motivo = Column(String(300), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    producto = relationship("Producto")
