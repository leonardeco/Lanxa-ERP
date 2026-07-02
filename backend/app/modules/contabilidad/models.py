"""
Super Ozono Global — Contabilidad Núcleo: Modelos SQLAlchemy
Basado en el Excel de Carga Inicial Contable y la documentación v2.0
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    String, Date, DateTime, Numeric, ForeignKey, Text,
    Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.time import utcnow
import enum


# ══════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════

class NaturalezaCuenta(str, enum.Enum):
    DEBITO = "Débito"
    CREDITO = "Crédito"


class ClaseCuenta(str, enum.Enum):
    ACTIVO = "Activo"
    PASIVO = "Pasivo"
    PATRIMONIO = "Patrimonio"
    INGRESO = "Ingreso"
    GASTO = "Gasto"
    COSTO = "Costo"


class NivelCuenta(str, enum.Enum):
    CLASE = "Clase"
    GRUPO = "Grupo"
    CUENTA = "Cuenta"
    SUBCUENTA = "Subcuenta"
    AUXILIAR = "Auxiliar"


class TipoCentroCosto(str, enum.Enum):
    MARCA = "Marca"
    AREA = "Área"
    PROYECTO = "Proyecto"


class EstadoPeriodo(str, enum.Enum):
    ABIERTO = "Abierto"
    CERRADO = "Cerrado"


class TipoTercero(str, enum.Enum):
    CLIENTE = "Cliente"
    PROVEEDOR = "Proveedor"
    EMPLEADO = "Empleado"
    MIXTO = "Mixto"


class TipoPersona(str, enum.Enum):
    NATURAL = "Natural"
    JURIDICA = "Jurídica"


class RegimenIVA(str, enum.Enum):
    RESPONSABLE = "Responsable"
    NO_RESPONSABLE = "No responsable"
    GRAN_CONTRIBUYENTE = "Gran contribuyente"


class EstadoDocumento(str, enum.Enum):
    PENDIENTE = "Pendiente"
    PARCIAL = "Parcial"
    PAGADO = "Pagado"
    VENCIDO = "Vencido"
    ANULADO = "Anulado"


# ══════════════════════════════════════════════════════════
# MODELOS
# ══════════════════════════════════════════════════════════

class PlanCuentas(Base):
    """Plan Único de Cuentas — PUC Colombiano (Decreto 2650)"""
    __tablename__ = "plan_cuentas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo_puc: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    clase: Mapped[ClaseCuenta] = mapped_column(SAEnum(ClaseCuenta))
    naturaleza: Mapped[NaturalezaCuenta] = mapped_column(SAEnum(NaturalezaCuenta))
    nivel: Mapped[NivelCuenta] = mapped_column(SAEnum(NivelCuenta), default=NivelCuenta.AUXILIAR)
    cuenta_padre_id: Mapped[int | None] = mapped_column(ForeignKey("plan_cuentas.id"))
    requiere_tercero: Mapped[bool] = mapped_column(default=False)
    requiere_centro_costo: Mapped[bool] = mapped_column(default=False)
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    cuenta_padre = relationship("PlanCuentas", remote_side=[id], backref="subcuentas")
    movimientos = relationship("MovimientoAsiento", back_populates="cuenta")
    saldos_iniciales = relationship("SaldoInicial", back_populates="cuenta")

    def __repr__(self):
        return f"<PlanCuentas {self.codigo_puc} - {self.nombre}>"


class CentroCosto(Base):
    """Centros de costo — Rentabilidad por marca / área"""
    __tablename__ = "centros_costo"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100))
    tipo: Mapped[TipoCentroCosto] = mapped_column(SAEnum(TipoCentroCosto))
    marca_asociada: Mapped[str | None] = mapped_column(String(100))
    responsable: Mapped[str | None] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(default=True)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    movimientos = relationship("MovimientoAsiento", back_populates="centro_costo")

    def __repr__(self):
        return f"<CentroCosto {self.codigo} - {self.nombre}>"


class PeriodoContable(Base):
    """Períodos contables — Cierre mensual y bloqueo"""
    __tablename__ = "periodos_contables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anio: Mapped[int] = mapped_column()
    mes: Mapped[int] = mapped_column()
    periodo: Mapped[str] = mapped_column(String(7), unique=True)  # "2026-01"
    estado: Mapped[EstadoPeriodo] = mapped_column(
        SAEnum(EstadoPeriodo), default=EstadoPeriodo.ABIERTO)
    fecha_cierre: Mapped[date | None] = mapped_column(Date)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("anio", "mes", name="uq_periodo_anio_mes"),
    )

    def __repr__(self):
        return f"<PeriodoContable {self.periodo} - {self.estado.value}>"


class Tercero(Base):
    """Registro único de terceros — Clientes, proveedores, empleados"""
    __tablename__ = "terceros"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nit_cc: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    dv: Mapped[str | None] = mapped_column(String(1))  # Dígito de verificación
    razon_social: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[TipoTercero] = mapped_column(SAEnum(TipoTercero))
    tipo_persona: Mapped[TipoPersona | None] = mapped_column(SAEnum(TipoPersona))
    regimen_iva: Mapped[RegimenIVA | None] = mapped_column(SAEnum(RegimenIVA))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    telefono: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(default=True)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self):
        return f"<Tercero {self.nit_cc} - {self.razon_social}>"


class AsientoContable(Base):
    """Cabecera de cada movimiento contable"""
    __tablename__ = "asientos_contables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha: Mapped[date] = mapped_column(Date)
    descripcion: Mapped[str] = mapped_column(String(500))
    tipo_documento: Mapped[str | None] = mapped_column(String(50))  # Factura, Recibo, Nota, etc.
    modulo_origen: Mapped[str | None] = mapped_column(String(50))  # ventas, compras, nomina, etc.
    usuario_id: Mapped[int | None] = mapped_column()  # FK a usuarios (futuro)
    periodo_id: Mapped[int | None] = mapped_column(ForeignKey("periodos_contables.id"))
    anulado: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    movimientos = relationship(
        "MovimientoAsiento", back_populates="asiento", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AsientoContable {self.id} - {self.fecha} - {self.descripcion[:30]}>"


class MovimientoAsiento(Base):
    """Débitos y créditos de cada asiento (partida doble)"""
    __tablename__ = "movimientos_asiento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asiento_id: Mapped[int] = mapped_column(ForeignKey("asientos_contables.id"))
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("plan_cuentas.id"))
    tercero_id: Mapped[int | None] = mapped_column(ForeignKey("terceros.id"))
    centro_costo_id: Mapped[int | None] = mapped_column(ForeignKey("centros_costo.id"))
    debito: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    credito: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    descripcion: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    # Relationships
    asiento = relationship("AsientoContable", back_populates="movimientos")
    cuenta = relationship("PlanCuentas", back_populates="movimientos")
    centro_costo = relationship("CentroCosto", back_populates="movimientos")

    def __repr__(self):
        return f"<MovimientoAsiento D:{self.debito} C:{self.credito}>"


class SaldoInicial(Base):
    """Saldos iniciales — Balance de apertura"""
    __tablename__ = "saldos_iniciales"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("plan_cuentas.id"))
    centro_costo_id: Mapped[int | None] = mapped_column(ForeignKey("centros_costo.id"))
    tercero_id: Mapped[int | None] = mapped_column(ForeignKey("terceros.id"))
    debito: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    credito: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)

    # Relationships
    cuenta = relationship("PlanCuentas", back_populates="saldos_iniciales")

    def __repr__(self):
        return f"<SaldoInicial Cuenta:{self.cuenta_id} D:{self.debito} C:{self.credito}>"


class CuentaPorCobrar(Base):
    """Cartera — Cuentas por Cobrar (CxC) inicial"""
    __tablename__ = "cuentas_por_cobrar"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_factura: Mapped[str] = mapped_column(String(50), unique=True)
    fecha_emision: Mapped[date] = mapped_column(Date)
    cliente_nit: Mapped[str] = mapped_column(String(20))
    nombre_cliente: Mapped[str | None] = mapped_column(String(200))
    marca: Mapped[str | None] = mapped_column(String(100))
    valor_factura: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    abonos: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    saldo_pendiente: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))  # Calculado
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[EstadoDocumento] = mapped_column(
        SAEnum(EstadoDocumento), default=EstadoDocumento.PENDIENTE)
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CuentaPorPagar(Base):
    """Cuentas por Pagar (CxP) inicial"""
    __tablename__ = "cuentas_por_pagar"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_documento: Mapped[str] = mapped_column(String(50), unique=True)
    fecha: Mapped[date] = mapped_column(Date)
    proveedor_nit: Mapped[str] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(200))
    concepto: Mapped[str | None] = mapped_column(String(300))
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    abonos: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    saldo_pendiente: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))  # Calculado
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[EstadoDocumento] = mapped_column(
        SAEnum(EstadoDocumento), default=EstadoDocumento.PENDIENTE)
    compra_id: Mapped[int | None] = mapped_column()  # FK lógica a compras.compradocumento
    notas: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TipoPago(str, enum.Enum):
    CXC = "CxC"
    CXP = "CxP"


class Pago(Base):
    """Comprobante de pago — Recibo de Caja (CxC) o Comprobante de Egreso (CxP)"""
    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    numero_comprobante: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    tipo: Mapped[TipoPago] = mapped_column(SAEnum(TipoPago))
    cxc_id: Mapped[int | None] = mapped_column(index=True)  # FK lógica a cuentas_por_cobrar
    cxp_id: Mapped[int | None] = mapped_column(index=True)  # FK lógica a cuentas_por_pagar
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    saldo_anterior: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    saldo_nuevo: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    notas: Mapped[str | None] = mapped_column(Text)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)


class ParametroTributario(Base):
    """Parámetros tributarios — Tarifas IVA, retenciones, etc."""
    __tablename__ = "parametros_tributarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concepto: Mapped[str] = mapped_column(String(200), unique=True)
    tarifa_valor: Mapped[Decimal | None] = mapped_column(Numeric(10, 5))
    base_aplica: Mapped[str | None] = mapped_column(String(200))
    cuenta_puc: Mapped[str | None] = mapped_column(String(20))
    notas: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ParametroNomina(Base):
    """Parámetros de nómina — SMMLV, aportes, parafiscales"""
    __tablename__ = "parametros_nomina"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concepto: Mapped[str] = mapped_column(String(200), unique=True)
    valor_porcentaje: Mapped[Decimal | None] = mapped_column(Numeric(12, 5))
    tipo: Mapped[str | None] = mapped_column(String(20))  # %, $, x SMMLV
    notas: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
