"""
Super Ozono Global — Contabilidad Núcleo: Modelos SQLAlchemy
Basado en el Excel de Carga Inicial Contable y la documentación v2.0
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    Numeric, ForeignKey, Text, Enum as SAEnum, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.core.database import Base
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_puc = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    clase = Column(SAEnum(ClaseCuenta), nullable=False)
    naturaleza = Column(SAEnum(NaturalezaCuenta), nullable=False)
    nivel = Column(SAEnum(NivelCuenta), nullable=False, default=NivelCuenta.AUXILIAR)
    cuenta_padre_id = Column(Integer, ForeignKey("plan_cuentas.id"), nullable=True)
    requiere_tercero = Column(Boolean, default=False)
    requiere_centro_costo = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cuenta_padre = relationship("PlanCuentas", remote_side=[id], backref="subcuentas")
    movimientos = relationship("MovimientoAsiento", back_populates="cuenta")
    saldos_iniciales = relationship("SaldoInicial", back_populates="cuenta")

    def __repr__(self):
        return f"<PlanCuentas {self.codigo_puc} - {self.nombre}>"


class CentroCosto(Base):
    """Centros de costo — Rentabilidad por marca / área"""
    __tablename__ = "centros_costo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    tipo = Column(SAEnum(TipoCentroCosto), nullable=False)
    marca_asociada = Column(String(100), nullable=True)
    responsable = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    movimientos = relationship("MovimientoAsiento", back_populates="centro_costo")

    def __repr__(self):
        return f"<CentroCosto {self.codigo} - {self.nombre}>"


class PeriodoContable(Base):
    """Períodos contables — Cierre mensual y bloqueo"""
    __tablename__ = "periodos_contables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    periodo = Column(String(7), nullable=False, unique=True)  # "2026-01"
    estado = Column(SAEnum(EstadoPeriodo), default=EstadoPeriodo.ABIERTO, nullable=False)
    fecha_cierre = Column(Date, nullable=True)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("anio", "mes", name="uq_periodo_anio_mes"),
    )

    def __repr__(self):
        return f"<PeriodoContable {self.periodo} - {self.estado.value}>"


class Tercero(Base):
    """Registro único de terceros — Clientes, proveedores, empleados"""
    __tablename__ = "terceros"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nit_cc = Column(String(20), unique=True, nullable=False, index=True)
    dv = Column(String(1), nullable=True)  # Dígito de verificación
    razon_social = Column(String(200), nullable=False)
    tipo = Column(SAEnum(TipoTercero), nullable=False)
    tipo_persona = Column(SAEnum(TipoPersona), nullable=True)
    regimen_iva = Column(SAEnum(RegimenIVA), nullable=True)
    ciudad = Column(String(100), nullable=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Tercero {self.nit_cc} - {self.razon_social}>"


class AsientoContable(Base):
    """Cabecera de cada movimiento contable"""
    __tablename__ = "asientos_contables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False)
    descripcion = Column(String(500), nullable=False)
    tipo_documento = Column(String(50), nullable=True)  # Factura, Recibo, Nota, etc.
    modulo_origen = Column(String(50), nullable=True)  # ventas, compras, nomina, etc.
    usuario_id = Column(Integer, nullable=True)  # FK a usuarios (futuro)
    periodo_id = Column(Integer, ForeignKey("periodos_contables.id"), nullable=True)
    anulado = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    movimientos = relationship("MovimientoAsiento", back_populates="asiento", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AsientoContable {self.id} - {self.fecha} - {self.descripcion[:30]}>"


class MovimientoAsiento(Base):
    """Débitos y créditos de cada asiento (partida doble)"""
    __tablename__ = "movimientos_asiento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asiento_id = Column(Integer, ForeignKey("asientos_contables.id"), nullable=False)
    cuenta_id = Column(Integer, ForeignKey("plan_cuentas.id"), nullable=False)
    tercero_id = Column(Integer, ForeignKey("terceros.id"), nullable=True)
    centro_costo_id = Column(Integer, ForeignKey("centros_costo.id"), nullable=True)
    debito = Column(Numeric(18, 2), default=Decimal("0.00"))
    credito = Column(Numeric(18, 2), default=Decimal("0.00"))
    descripcion = Column(String(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    asiento = relationship("AsientoContable", back_populates="movimientos")
    cuenta = relationship("PlanCuentas", back_populates="movimientos")
    centro_costo = relationship("CentroCosto", back_populates="movimientos")

    def __repr__(self):
        return f"<MovimientoAsiento D:{self.debito} C:{self.credito}>"


class SaldoInicial(Base):
    """Saldos iniciales — Balance de apertura"""
    __tablename__ = "saldos_iniciales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuenta_id = Column(Integer, ForeignKey("plan_cuentas.id"), nullable=False)
    centro_costo_id = Column(Integer, ForeignKey("centros_costo.id"), nullable=True)
    tercero_id = Column(Integer, ForeignKey("terceros.id"), nullable=True)
    debito = Column(Numeric(18, 2), default=Decimal("0.00"))
    credito = Column(Numeric(18, 2), default=Decimal("0.00"))
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    cuenta = relationship("PlanCuentas", back_populates="saldos_iniciales")

    def __repr__(self):
        return f"<SaldoInicial Cuenta:{self.cuenta_id} D:{self.debito} C:{self.credito}>"


class CuentaPorCobrar(Base):
    """Cartera — Cuentas por Cobrar (CxC) inicial"""
    __tablename__ = "cuentas_por_cobrar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_factura = Column(String(50), unique=True, nullable=False)
    fecha_emision = Column(Date, nullable=False)
    cliente_nit = Column(String(20), nullable=False)
    nombre_cliente = Column(String(200), nullable=True)
    marca = Column(String(100), nullable=True)
    valor_factura = Column(Numeric(18, 2), nullable=False)
    abonos = Column(Numeric(18, 2), default=Decimal("0.00"))
    saldo_pendiente = Column(Numeric(18, 2), nullable=True)  # Calculado
    fecha_vencimiento = Column(Date, nullable=True)
    estado = Column(SAEnum(EstadoDocumento), default=EstadoDocumento.PENDIENTE)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CuentaPorPagar(Base):
    """Cuentas por Pagar (CxP) inicial"""
    __tablename__ = "cuentas_por_pagar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_documento = Column(String(50), unique=True, nullable=False)
    fecha = Column(Date, nullable=False)
    proveedor_nit = Column(String(20), nullable=False)
    razon_social = Column(String(200), nullable=True)
    concepto = Column(String(300), nullable=True)
    valor = Column(Numeric(18, 2), nullable=False)
    abonos = Column(Numeric(18, 2), default=Decimal("0.00"))
    saldo_pendiente = Column(Numeric(18, 2), nullable=True)  # Calculado
    fecha_vencimiento = Column(Date, nullable=True)
    estado = Column(SAEnum(EstadoDocumento), default=EstadoDocumento.PENDIENTE)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ParametroTributario(Base):
    """Parámetros tributarios — Tarifas IVA, retenciones, etc."""
    __tablename__ = "parametros_tributarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concepto = Column(String(200), nullable=False, unique=True)
    tarifa_valor = Column(Numeric(10, 5), nullable=True)
    base_aplica = Column(String(200), nullable=True)
    cuenta_puc = Column(String(20), nullable=True)
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ParametroNomina(Base):
    """Parámetros de nómina — SMMLV, aportes, parafiscales"""
    __tablename__ = "parametros_nomina"

    id = Column(Integer, primary_key=True, autoincrement=True)
    concepto = Column(String(200), nullable=False, unique=True)
    valor_porcentaje = Column(Numeric(12, 5), nullable=True)
    tipo = Column(String(20), nullable=True)  # %, $, x SMMLV
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



