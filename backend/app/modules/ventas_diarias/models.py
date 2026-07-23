"""
Super Ozono Global — Módulo Ventas Diarias (Run 6)
Ventas contraentrega por guía de transportadora — flujo Perú/Ecuador,
separado del módulo `ventas` (Colombia: IVA, retenciones, Alegra).
"""

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    String, Date, DateTime, Numeric, ForeignKey, Text, Boolean, Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.tenancy import TenantScoped
from app.core.time import utcnow
import enum


class EstadoVentaDiaria(str, enum.Enum):
    PENDIENTE = "Pendiente"
    ENTREGADO = "Entregado"
    EN_DESTINO = "En destino"
    DEVOLUCION = "Devolución"


class VentaDiaria(TenantScoped, Base):
    """Cabecera de una venta contraentrega — una guía, uno o más productos."""
    __tablename__ = "ventas_diarias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    asesor: Mapped[str | None] = mapped_column(String(200))
    guia: Mapped[str | None] = mapped_column(String(50), index=True)
    codigo_guia: Mapped[str | None] = mapped_column(String(20))
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    estado: Mapped[EstadoVentaDiaria] = mapped_column(
        SAEnum(EstadoVentaDiaria), default=EstadoVentaDiaria.PENDIENTE)
    forma_pago: Mapped[str | None] = mapped_column(String(100))
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow)

    cliente = relationship("Cliente")
    detalles = relationship(
        "VentaDiariaDetalle", back_populates="venta_diaria",
        cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VentaDiaria {self.guia} - {self.fecha}>"


class VentaDiariaDetalle(TenantScoped, Base):
    """Línea de producto dentro de una guía. Abono/saldo se lleva por línea,
    igual que en el Excel de origen (no por cabecera)."""
    __tablename__ = "ventas_diarias_detalles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    venta_diaria_id: Mapped[int] = mapped_column(ForeignKey("ventas_diarias.id"), index=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1.00"))
    venta: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    abono_1: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    abono_2: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    saldo: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    # Datos crudos del Excel de origen sin significado confirmado (ver
    # "Preguntas abiertas" en el design doc de este Run) — no usar en
    # reportes hasta que la auxiliar de Perú confirme qué representan.
    pesos_c: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    valor_flete: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    venta_diaria = relationship("VentaDiaria", back_populates="detalles")
    producto = relationship("Producto")

    def __repr__(self):
        return f"<VentaDiariaDetalle Prod:{self.producto_id} Saldo:{self.saldo}>"


class PagoSuelto(TenantScoped, Base):
    """Abonos sueltos importados del Excel, vinculados al cliente solo por
    nombre en texto (sin guía/producto) — quedan marcados para revisión
    manual; no se intenta adivinar a cuál venta abonan."""
    __tablename__ = "pagos_sueltos_diarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha: Mapped[date] = mapped_column(Date, default=date.today)
    cliente_texto: Mapped[str] = mapped_column(String(300))
    monto: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    revisado: Mapped[bool] = mapped_column(Boolean, default=False)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    def __repr__(self):
        return f"<PagoSuelto {self.cliente_texto} - {self.monto}>"
