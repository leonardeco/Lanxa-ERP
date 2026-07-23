# Run 6: Tenant Perú + Ventas Diarias — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dar de alta Perú como tenant separado del ERP (misma LAN/SQLite),
con un módulo de ventas propio (`VentaDiaria`) calcado del flujo real de
contraentrega, importar el histórico de `SUPEROZONO PERU DIARIAS.xlsx`
(Enero–Julio 2026) y habilitar captura en vivo desde la UI.

**Architecture:** nuevo módulo backend `app/modules/ventas_diarias/`
(modelos, schemas, router) independiente del módulo `ventas` de Colombia
(que trae IVA/retenciones/Alegra, no aplicables a Perú). Reutiliza
`Producto`/`Cliente` (ya `TenantScoped`) y la infraestructura de tenancy ya
construida (Runs 2–5): el aislamiento real en este despliegue LAN/SQLite es
el filtro a nivel de aplicación (`for_tenant`/`get_for_tenant`/stamp en
insert), no RLS de Postgres (no-op en SQLite).

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic (backend),
React + TypeScript (frontend), pytest + httpx (tests backend), Playwright
(verificación E2E manual, se instala temporalmente).

**Diseño completo:** `docs/hydraia/plans/2026-07-23-run6-peru-tenant-ventas-diarias.md`

## Global Constraints

- No tocar el módulo `ventas` existente (Colombia) — módulo nuevo separado.
- Todo query de listado/detalle sobre las tablas nuevas debe pasar por
  `for_tenant`/`get_for_tenant` (nunca un `select(Model)` desnudo) — es la
  única defensa real de aislamiento en el despliegue LAN/SQLite actual.
- Cambios de auth/sesión/tenant se verifican con un paso real en navegador
  (Chromium), no solo con pytest — regla ya establecida en este proyecto.
- Rutas literales (`/resumen/...`, `/pagos-sueltos/...`) deben declararse
  **antes** que la ruta genérica `/{venta_diaria_id}` en el router, o
  FastAPI intentará convertir "resumen"/"pagos-sueltos" a `int` y fallará
  con 422 en vez de enrutar correctamente.
- Alembic: cualquier tabla nueva debe registrarse en `alembic/env.py`
  (import del módulo de modelos) o `alembic check` en CI verá la tabla
  como "no gestionada" y marcará drift.

---

### Task 1: Modelos ORM + migración Alembic

**Files:**
- Create: `backend/app/modules/ventas_diarias/__init__.py`
- Create: `backend/app/modules/ventas_diarias/models.py`
- Create: `backend/alembic/versions/a9b8c7d6e5f4_ventas_diarias.py`
- Modify: `backend/alembic/env.py`
- Modify: `backend/app/core/tenancy.py` (RLS_TABLES)

**Interfaces:**
- Produces: `EstadoVentaDiaria` (str enum: `PENDIENTE`, `ENTREGADO`,
  `EN_DESTINO`, `DEVOLUCION` — valores `"Pendiente"`, `"Entregado"`,
  `"En destino"`, `"Devolución"`), `VentaDiaria`, `VentaDiariaDetalle`,
  `PagoSuelto` (todas `TenantScoped`, tabla `ventas_diarias`,
  `ventas_diarias_detalles`, `pagos_sueltos_diarios`).

- [ ] **Step 1: Crear el módulo y los modelos**

`backend/app/modules/ventas_diarias/__init__.py` (vacío):

```python
```

`backend/app/modules/ventas_diarias/models.py`:

```python
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
    venta_diaria_id: Mapped[int] = mapped_column(ForeignKey("ventas_diarias.id"))
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
```

- [ ] **Step 2: Registrar el módulo en Alembic `env.py`**

En `backend/alembic/env.py`, junto a los demás imports de modelos:

```python
from app.modules.ventas import models as _ventas_models  # noqa: F401
from app.modules.ventas_diarias import models as _ventas_diarias_models  # noqa: F401
```

- [ ] **Step 3: Agregar las tablas nuevas a `RLS_TABLES`**

En `backend/app/core/tenancy.py`, dentro de la tupla `RLS_TABLES`, agregar
después de `"lotes",`:

```python
    "lotes",
    "document_sequences",
    "ventas_diarias",
    "ventas_diarias_detalles",
    "pagos_sueltos_diarios",
)
```

(reemplaza la línea de cierre `)` existente — quedan 3 tablas nuevas antes
del paréntesis final).

- [ ] **Step 4: Migración Alembic**

`backend/alembic/versions/a9b8c7d6e5f4_ventas_diarias.py`:

```python
"""ventas_diarias: modulo de ventas contraentrega (Peru/Ecuador, Run 6)

Revision ID: a9b8c7d6e5f4
Revises: c6d7e8f9a0b1
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "a9b8c7d6e5f4"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ventas_diarias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("asesor", sa.String(length=200), nullable=True),
        sa.Column("guia", sa.String(length=50), nullable=True),
        sa.Column("codigo_guia", sa.String(length=20), nullable=True),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column(
            "estado",
            sa.Enum("PENDIENTE", "ENTREGADO", "EN_DESTINO", "DEVOLUCION",
                    name="estadoventadiaria"),
            nullable=False,
        ),
        sa.Column("forma_pago", sa.String(length=100), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ventas_diarias_tenant_id", "ventas_diarias", ["tenant_id"])
    op.create_index("ix_ventas_diarias_guia", "ventas_diarias", ["guia"])

    op.create_table(
        "ventas_diarias_detalles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("venta_diaria_id", sa.Integer(), nullable=False),
        sa.Column("producto_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Numeric(12, 2), nullable=False),
        sa.Column("venta", sa.Numeric(18, 2), nullable=True),
        sa.Column("abono_1", sa.Numeric(18, 2), nullable=True),
        sa.Column("abono_2", sa.Numeric(18, 2), nullable=True),
        sa.Column("saldo", sa.Numeric(18, 2), nullable=False),
        sa.Column("pesos_c", sa.Numeric(18, 2), nullable=True),
        sa.Column("valor_flete", sa.Numeric(18, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["venta_diaria_id"], ["ventas_diarias.id"]),
        sa.ForeignKeyConstraint(["producto_id"], ["productos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ventas_diarias_detalles_tenant_id", "ventas_diarias_detalles", ["tenant_id"])
    op.create_index(
        "ix_ventas_diarias_detalles_venta_diaria_id",
        "ventas_diarias_detalles", ["venta_diaria_id"])

    op.create_table(
        "pagos_sueltos_diarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("cliente_texto", sa.String(length=300), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("revisado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pagos_sueltos_diarios_tenant_id", "pagos_sueltos_diarios", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("pagos_sueltos_diarios")
    op.drop_index(
        "ix_ventas_diarias_detalles_venta_diaria_id", table_name="ventas_diarias_detalles")
    op.drop_index("ix_ventas_diarias_detalles_tenant_id", table_name="ventas_diarias_detalles")
    op.drop_table("ventas_diarias_detalles")
    op.drop_index("ix_ventas_diarias_guia", table_name="ventas_diarias")
    op.drop_index("ix_ventas_diarias_tenant_id", table_name="ventas_diarias")
    op.drop_table("ventas_diarias")
    sa.Enum(name="estadoventadiaria").drop(op.get_bind(), checkfirst=True)
```

- [ ] **Step 5: Verificar que la migración corre en limpio contra Postgres de test**

Run: `cd backend && python -m alembic upgrade head`
Expected: aplica `a9b8c7d6e5f4` sin error (requiere `TEST_DATABASE_URL`/`.env`
apuntando a un Postgres local — ver `ops/TESTES-LOCAL-POSTGRES.md`).

Run: `cd backend && python -m alembic check`
Expected: `No new upgrade operations detected.` (sin drift entre modelos y migración).

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/ventas_diarias/__init__.py backend/app/modules/ventas_diarias/models.py backend/alembic/versions/a9b8c7d6e5f4_ventas_diarias.py backend/alembic/env.py backend/app/core/tenancy.py
git commit -m "feat(ventas-diarias): modelos VentaDiaria/VentaDiariaDetalle/PagoSuelto + migración"
```

---

### Task 2: Schemas Pydantic

**Files:**
- Create: `backend/app/modules/ventas_diarias/schemas.py`

**Interfaces:**
- Consumes: `EstadoVentaDiaria` (Task 1).
- Produces: `VentaDiariaCreate`, `VentaDiariaResponse`,
  `VentaDiariaDetalleCreate`, `VentaDiariaDetalleResponse`,
  `VentaDiariaResumenMensual`, `PagoSueltoResponse`, `PagoSueltoUpdate`.

- [ ] **Step 1: Escribir los schemas**

`backend/app/modules/ventas_diarias/schemas.py`:

```python
"""
Super Ozono Global — Schemas Pydantic para Ventas Diarias (Run 6)
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class VentaDiariaDetalleCreate(BaseModel):
    producto_id: int
    cantidad: Decimal = Field(default=Decimal("1.00"), gt=0)
    venta: Optional[Decimal] = Field(default=None, ge=0)
    abono_1: Optional[Decimal] = Field(default=None, ge=0)
    abono_2: Optional[Decimal] = Field(default=None, ge=0)
    pesos_c: Optional[Decimal] = None
    valor_flete: Optional[Decimal] = None


class VentaDiariaDetalleResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: Decimal
    venta: Optional[Decimal] = None
    abono_1: Optional[Decimal] = None
    abono_2: Optional[Decimal] = None
    saldo: Decimal
    pesos_c: Optional[Decimal] = None
    valor_flete: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class VentaDiariaCreate(BaseModel):
    fecha: date
    asesor: Optional[str] = Field(default=None, max_length=200)
    guia: Optional[str] = Field(default=None, max_length=50)
    codigo_guia: Optional[str] = Field(default=None, max_length=20)
    cliente_id: int
    estado: str = "Pendiente"
    forma_pago: Optional[str] = Field(default=None, max_length=100)
    notas: Optional[str] = None
    detalles: List[VentaDiariaDetalleCreate] = Field(min_length=1)


class VentaDiariaResponse(BaseModel):
    id: int
    fecha: date
    asesor: Optional[str] = None
    guia: Optional[str] = None
    codigo_guia: Optional[str] = None
    cliente_id: int
    estado: str
    forma_pago: Optional[str] = None
    notas: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    detalles: List[VentaDiariaDetalleResponse] = []

    model_config = {"from_attributes": True}


class VentaDiariaResumenMensual(BaseModel):
    anio: int
    mes: int
    total_venta: Decimal
    total_abonado: Decimal
    total_saldo: Decimal
    cantidad_entregado: int
    cantidad_devolucion: int


class PagoSueltoResponse(BaseModel):
    id: int
    fecha: date
    cliente_texto: str
    monto: Decimal
    revisado: bool
    notas: Optional[str] = None

    model_config = {"from_attributes": True}


class PagoSueltoUpdate(BaseModel):
    revisado: bool
```

- [ ] **Step 2: Verificar que importa sin errores**

Run: `cd backend && python -c "from app.modules.ventas_diarias import schemas"`
Expected: sin salida (import limpio, sin excepción).

- [ ] **Step 3: Commit**

```bash
git add backend/app/modules/ventas_diarias/schemas.py
git commit -m "feat(ventas-diarias): schemas Pydantic"
```

---

### Task 3: Router (endpoints) + registro en la app

**Files:**
- Create: `backend/app/modules/ventas_diarias/router.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: modelos de Task 1, schemas de Task 2, `for_tenant`/
  `get_for_tenant` (`app.core.tenancy`), `ContableDep` (`app.api.deps`),
  `Cliente`/`Producto` (`app.modules.ventas.models`).
- Produces: `router` (prefix `/api/v1/ventas-diarias`) con:
  `GET /`, `POST /`, `GET /{venta_diaria_id}`,
  `GET /resumen/{anio}/{mes}`, `GET /pagos-sueltos/`,
  `PATCH /pagos-sueltos/{pago_id}`.

- [ ] **Step 1: Escribir el router**

`backend/app/modules/ventas_diarias/router.py`:

```python
"""
Super Ozono Global — API Routes (Ventas Diarias, Run 6)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from decimal import Decimal
from datetime import date

from app.core.database import get_db
from app.core.tenancy import for_tenant, get_for_tenant
from app.api.deps import ContableDep
from app.modules.ventas.models import Cliente, Producto
from app.modules.ventas_diarias.models import (
    VentaDiaria, VentaDiariaDetalle, PagoSuelto, EstadoVentaDiaria,
)
from app.modules.ventas_diarias.schemas import (
    VentaDiariaCreate, VentaDiariaResponse,
    VentaDiariaResumenMensual, PagoSueltoResponse, PagoSueltoUpdate,
)

router = APIRouter(prefix="/api/v1/ventas-diarias", tags=["Ventas Diarias"])

_EAGER = (selectinload(VentaDiaria.detalles),)


def _calcular_saldo(
    venta: Optional[Decimal], abono_1: Optional[Decimal], abono_2: Optional[Decimal]
) -> Decimal:
    v = venta or Decimal("0")
    a1 = abono_1 or Decimal("0")
    a2 = abono_2 or Decimal("0")
    return v - a1 - a2


async def _get_venta_diaria_or_404(db: AsyncSession, venta_diaria_id: int) -> VentaDiaria:
    venta = await db.scalar(
        for_tenant(
            select(VentaDiaria).options(*_EAGER).where(VentaDiaria.id == venta_diaria_id),
            VentaDiaria,
        )
    )
    if not venta:
        raise HTTPException(status_code=404, detail="Venta diaria no encontrada")
    return venta


@router.get("/", response_model=List[VentaDiariaResponse])
async def list_ventas_diarias(
    _: ContableDep,
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    estado: Optional[str] = Query(None),
    asesor: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Listar ventas diarias del tenant actual (paginado, mas recientes primero)."""
    query = for_tenant(
        select(VentaDiaria).options(*_EAGER)
        .order_by(desc(VentaDiaria.fecha), desc(VentaDiaria.id))
        .limit(limit).offset(offset),
        VentaDiaria,
    )
    if fecha_desde:
        query = query.where(VentaDiaria.fecha >= fecha_desde)
    if fecha_hasta:
        query = query.where(VentaDiaria.fecha <= fecha_hasta)
    if estado:
        query = query.where(VentaDiaria.estado == estado)
    if asesor:
        query = query.where(VentaDiaria.asesor == asesor)
    rows = (await db.execute(query)).scalars().unique().all()
    return rows


@router.post("/", response_model=VentaDiariaResponse, status_code=201)
async def create_venta_diaria(
    data: VentaDiariaCreate, _: ContableDep, db: AsyncSession = Depends(get_db),
):
    """Crear una venta diaria con sus lineas de producto. El saldo de cada
    linea se calcula en el servidor (venta - abono_1 - abono_2), nunca se
    acepta del cliente."""
    cliente = await get_for_tenant(db, Cliente, data.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    venta = VentaDiaria(
        fecha=data.fecha,
        asesor=data.asesor,
        guia=data.guia,
        codigo_guia=data.codigo_guia,
        cliente_id=data.cliente_id,
        estado=EstadoVentaDiaria(data.estado),
        forma_pago=data.forma_pago,
        notas=data.notas,
    )
    db.add(venta)
    await db.flush()

    for linea in data.detalles:
        producto = await get_for_tenant(db, Producto, linea.producto_id)
        if not producto:
            raise HTTPException(
                status_code=404, detail=f"Producto {linea.producto_id} no encontrado")
        db.add(VentaDiariaDetalle(
            venta_diaria_id=venta.id,
            producto_id=linea.producto_id,
            cantidad=linea.cantidad,
            venta=linea.venta,
            abono_1=linea.abono_1,
            abono_2=linea.abono_2,
            saldo=_calcular_saldo(linea.venta, linea.abono_1, linea.abono_2),
            pesos_c=linea.pesos_c,
            valor_flete=linea.valor_flete,
        ))

    await db.flush()
    return await _get_venta_diaria_or_404(db, venta.id)


@router.get("/resumen/{anio}/{mes}", response_model=VentaDiariaResumenMensual)
async def resumen_mensual(
    anio: int, mes: int, _: ContableDep, db: AsyncSession = Depends(get_db),
):
    """Totales del mes para el tenant actual: venta, abonado, saldo pendiente
    y conteo de entregados/devoluciones."""
    totales_query = for_tenant(
        select(
            func.coalesce(func.sum(VentaDiariaDetalle.venta), 0),
            func.coalesce(
                func.sum(
                    func.coalesce(VentaDiariaDetalle.abono_1, 0)
                    + func.coalesce(VentaDiariaDetalle.abono_2, 0)
                ),
                0,
            ),
            func.coalesce(func.sum(VentaDiariaDetalle.saldo), 0),
        )
        .join(VentaDiaria, VentaDiaria.id == VentaDiariaDetalle.venta_diaria_id)
        .where(
            extract("year", VentaDiaria.fecha) == anio,
            extract("month", VentaDiaria.fecha) == mes,
        ),
        VentaDiariaDetalle,
    )
    total_venta, total_abonado, total_saldo = (await db.execute(totales_query)).one()

    conteo_query = for_tenant(
        select(VentaDiaria.estado, func.count(VentaDiaria.id))
        .where(
            extract("year", VentaDiaria.fecha) == anio,
            extract("month", VentaDiaria.fecha) == mes,
        )
        .group_by(VentaDiaria.estado),
        VentaDiaria,
    )
    conteos = dict((await db.execute(conteo_query)).all())

    return VentaDiariaResumenMensual(
        anio=anio,
        mes=mes,
        total_venta=total_venta,
        total_abonado=total_abonado,
        total_saldo=total_saldo,
        cantidad_entregado=conteos.get(EstadoVentaDiaria.ENTREGADO, 0),
        cantidad_devolucion=conteos.get(EstadoVentaDiaria.DEVOLUCION, 0),
    )


@router.get("/pagos-sueltos/", response_model=List[PagoSueltoResponse])
async def list_pagos_sueltos(
    _: ContableDep,
    revisado: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = for_tenant(
        select(PagoSuelto).order_by(desc(PagoSuelto.fecha)), PagoSuelto)
    if revisado is not None:
        query = query.where(PagoSuelto.revisado == revisado)
    rows = (await db.execute(query)).scalars().all()
    return rows


@router.patch("/pagos-sueltos/{pago_id}", response_model=PagoSueltoResponse)
async def marcar_pago_suelto(
    pago_id: int, data: PagoSueltoUpdate, _: ContableDep,
    db: AsyncSession = Depends(get_db),
):
    pago = await get_for_tenant(db, PagoSuelto, pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago suelto no encontrado")
    pago.revisado = data.revisado
    await db.flush()
    return pago


@router.get("/{venta_diaria_id}", response_model=VentaDiariaResponse)
async def get_venta_diaria(
    venta_diaria_id: int, _: ContableDep, db: AsyncSession = Depends(get_db),
):
    return await _get_venta_diaria_or_404(db, venta_diaria_id)
```

**Nota de orden de rutas:** `/resumen/{anio}/{mes}` y `/pagos-sueltos/...`
están declaradas **antes** que `/{venta_diaria_id}` a propósito — si
`/{venta_diaria_id}` fuera primero, FastAPI intentaría convertir
`"resumen"`/`"pagos-sueltos"` a `int` y devolvería 422 en vez de enrutar
a los endpoints correctos.

- [ ] **Step 2: Registrar el router en `main.py`**

En `backend/app/main.py`, junto a los demás imports de routers:

```python
from app.modules.tenancy.router import router as tenancy_router
from app.modules.ventas_diarias.router import router as ventas_diarias_router
```

Y junto a los `app.include_router(...)`:

```python
app.include_router(tenancy_router)
app.include_router(ventas_diarias_router)
```

- [ ] **Step 3: Verificar que la app arranca**

Run: `cd backend && python -c "from app.main import app; print(len(app.routes))"`
Expected: imprime un número (sin excepción de importación/registro de rutas).

- [ ] **Step 4: Commit**

```bash
git add backend/app/modules/ventas_diarias/router.py backend/app/main.py
git commit -m "feat(ventas-diarias): endpoints CRUD, resumen mensual y pagos sueltos"
```

---

### Task 4: Tests CRUD y resumen mensual

**Files:**
- Create: `backend/tests/test_ventas_diarias.py`

**Interfaces:**
- Consumes: fixtures `client`, `auth_headers`, `db_session`
  (`backend/tests/conftest.py`), endpoints de Task 3.

- [ ] **Step 1: Escribir los tests**

`backend/tests/test_ventas_diarias.py`:

```python
"""Run 6 — CRUD y resumen mensual de Ventas Diarias."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _crear_producto(client: AsyncClient, auth_headers: dict, sku: str) -> int:
    r = await client.post(
        "/api/v1/ventas/productos",
        headers=auth_headers,
        json={
            "sku": sku,
            "nombre": f"Producto {sku}",
            "marca": "Test",
            "precio_venta": "100",
            "stock_actual": 10,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _crear_cliente(client: AsyncClient, auth_headers: dict, nit_cc: str) -> int:
    r = await client.post(
        "/api/v1/ventas/clientes",
        headers=auth_headers,
        json={
            "nit_cc": nit_cc,
            "razon_social": f"Cliente {nit_cc}",
            "tipo_persona": "Natural",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_crear_venta_diaria_calcula_saldo(client: AsyncClient, auth_headers: dict):
    producto_id = await _crear_producto(client, auth_headers, "PE-BIOCIDA")
    cliente_id = await _crear_cliente(client, auth_headers, "45095067")

    r = await client.post(
        "/api/v1/ventas-diarias/",
        headers=auth_headers,
        json={
            "fecha": "2026-01-28",
            "asesor": "MIGUEL B",
            "guia": "70223232",
            "codigo_guia": "KWHT",
            "cliente_id": cliente_id,
            "estado": "Entregado",
            "forma_pago": "Contraentrega",
            "detalles": [
                {"producto_id": producto_id, "cantidad": 2, "venta": 238, "abono_1": 30},
            ],
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert float(body["detalles"][0]["saldo"]) == 208.0


@pytest.mark.asyncio
async def test_listar_ventas_diarias_filtra_por_estado(client: AsyncClient, auth_headers: dict):
    producto_id = await _crear_producto(client, auth_headers, "PE-STAR")
    cliente_id = await _crear_cliente(client, auth_headers, "76307082")

    await client.post(
        "/api/v1/ventas-diarias/",
        headers=auth_headers,
        json={
            "fecha": "2026-01-03",
            "cliente_id": cliente_id,
            "estado": "Devolución",
            "detalles": [{"producto_id": producto_id, "cantidad": 1, "venta": 100}],
        },
    )

    r = await client.get(
        "/api/v1/ventas-diarias/", headers=auth_headers, params={"estado": "Devolución"})
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    assert r.json()[0]["estado"] == "Devolución"


@pytest.mark.asyncio
async def test_resumen_mensual_suma_ventas_y_saldos(client: AsyncClient, auth_headers: dict):
    producto_id = await _crear_producto(client, auth_headers, "PE-SUELO")
    cliente_id = await _crear_cliente(client, auth_headers, "19226409")

    await client.post(
        "/api/v1/ventas-diarias/",
        headers=auth_headers,
        json={
            "fecha": "2026-02-10",
            "cliente_id": cliente_id,
            "estado": "Entregado",
            "detalles": [
                {"producto_id": producto_id, "cantidad": 1, "venta": 200, "abono_1": 50},
            ],
        },
    )

    r = await client.get("/api/v1/ventas-diarias/resumen/2026/2", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert float(body["total_venta"]) >= 200.0
    assert float(body["total_saldo"]) >= 150.0
    assert body["cantidad_entregado"] >= 1


@pytest.mark.asyncio
async def test_get_venta_diaria_inexistente_404(client: AsyncClient, auth_headers: dict):
    r = await client.get("/api/v1/ventas-diarias/999999", headers=auth_headers)
    assert r.status_code == 404
```

- [ ] **Step 2: Correr los tests y confirmar que fallan primero (sin router aun registrado sería 404; con Task 3 ya aplicado deberían pasar — si se ejecuta este Task de forma aislada antes de Task 3, confirmar el fallo esperado)**

Run: `cd backend && python -m pytest tests/test_ventas_diarias.py -v`
Expected (con Tasks 1-3 ya aplicados): todos los tests en verde.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_ventas_diarias.py
git commit -m "test(ventas-diarias): CRUD, filtro por estado y resumen mensual"
```

---

### Task 5: Test de aislamiento por tenant

**Files:**
- Modify: `backend/tests/test_tenant_http_isolation.py`

**Interfaces:**
- Consumes: `VentaDiaria`, `VentaDiariaDetalle` (Task 1), fixtures
  `client`/`auth_headers`/`db_session`, helpers `set_tenant_id`/
  `apply_rls_tenant`/`reset_tenant_id` ya importados en el archivo.

- [ ] **Step 1: Agregar el import del modelo nuevo**

En `backend/tests/test_tenant_http_isolation.py`, junto al import existente:

```python
from app.modules.ventas.models import Producto
from app.modules.ventas_diarias.models import VentaDiaria, VentaDiariaDetalle
```

- [ ] **Step 2: Agregar el test de aislamiento**

Al final del archivo:

```python
@pytest.mark.asyncio
async def test_list_ventas_diarias_no_ve_otro_tenant(
    client: AsyncClient, auth_headers: dict, db_session
):
    """Auxiliar del tenant 1 no ve ventas diarias del tenant 2."""
    from app.modules.ventas.models import Cliente

    db_session.add(Tenant(id=2, codigo="peru-test", razon_social="Peru Test", activo=True))
    await db_session.flush()

    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)
    producto = Producto(
        sku="PE-SECRET", nombre="Secreto", marca="X",
        precio_venta=Decimal("1"), stock_actual=Decimal("0"), tenant_id=2,
    )
    cliente = Cliente(nit_cc="99999999", razon_social="Cliente Secreto", tenant_id=2)
    db_session.add_all([producto, cliente])
    await db_session.flush()
    venta = VentaDiaria(
        fecha="2026-01-01", cliente_id=cliente.id, tenant_id=2,
    )
    db_session.add(venta)
    await db_session.flush()
    db_session.add(VentaDiariaDetalle(
        venta_diaria_id=venta.id, producto_id=producto.id,
        cantidad=Decimal("1"), venta=Decimal("100"), saldo=Decimal("100"),
        tenant_id=2,
    ))
    await db_session.commit()
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)

    r = await client.get("/api/v1/ventas-diarias/", headers=auth_headers)
    assert r.status_code == 200, r.text
    guias = {v["guia"] for v in r.json()}
    assert "PE-SECRET" not in guias  # ninguna fila del tenant 2 debe aparecer
    assert all(v["cliente_id"] != cliente.id for v in r.json())
```

- [ ] **Step 3: Correr el test**

Run: `cd backend && python -m pytest tests/test_tenant_http_isolation.py -v`
Expected: todos los tests en verde, incluido
`test_list_ventas_diarias_no_ve_otro_tenant`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_tenant_http_isolation.py
git commit -m "test(tenancy): aislamiento de ventas diarias entre tenants"
```

---

### Task 6: Alta del tenant Perú + usuario auxiliar

**Files:** ninguno (operación vía API contra el servidor real, no código).

**Interfaces:**
- Consumes: `POST /api/v1/tenants/onboard` (ya existe, Run 5).

- [ ] **Step 1: Levantar el backend local y loguearse como Superusuario**

Run: `cd backend && .\start.bat` (o el flujo habitual de arranque LAN)

- [ ] **Step 2: Obtener un token de Superusuario del tenant plataforma**

```bash
curl -k -X POST https://192.168.1.131:8000/api/login/access-token \
  -d "username=admin@superozonoglobal.com&password=<clave real del .env>"
```

Guardar el `access_token` de la respuesta.

- [ ] **Step 3: Dar de alta el tenant Perú**

```bash
curl -k -X POST https://192.168.1.131:8000/api/v1/tenants/onboard \
  -H "Authorization: Bearer <token del paso anterior>" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo": "peru",
    "razon_social": "Super Ozono Perú",
    "admin_email": "auxiliar.peru@superozonoglobal.com",
    "admin_nombre": "Auxiliar Contable Perú",
    "admin_password": "<clave temporal segura>"
  }'
```

Expected: `201`, respuesta con `tenant.id` (será el tenant Perú, ej. `id=2`)
y `admin_email` confirmado.

- [ ] **Step 4: Ajustar el rol del usuario creado (nace Superusuario del onboarding; bajar a Auxiliar Contable de su propio tenant)**

El endpoint de onboarding siempre crea el primer usuario como
`Superusuario` **de ese tenant** (aislado, no ve Colombia). Si se quiere
que la auxiliar de Perú tenga el rol operativo real (`Auxiliar Contable`)
en vez de administrar su propio tenant, actualizar el rol vía
`PATCH /api/v1/usuarios/{id}` autenticado como el Superusuario recién
creado de Perú (ver `usuarios/router.py` para el endpoint exacto de
edición de usuarios).

- [ ] **Step 5: Verificar login de la auxiliar de Perú**

```bash
curl -k -X POST https://192.168.1.131:8000/api/login/access-token \
  -d "username=auxiliar.peru@superozonoglobal.com&password=<clave temporal>"
```

Expected: `200` con `access_token`.

- [ ] **Step 6: Registrar en BITACORA.md**

Agregar una entrada `## Sesión — 2026-07-23` describiendo el alta del
tenant Perú (id, código, admin inicial) siguiendo el formato ya
establecido del archivo.

---

### Task 7: Script de importación del histórico Excel

**Files:**
- Create: `backend/scripts/import_peru_ventas_diarias.py`

**Interfaces:**
- Consumes: `async_session` (`app.core.database`), `set_tenant_id`/
  `apply_rls_tenant` (`app.core.tenancy`), `Producto`/`Cliente`
  (`app.modules.ventas.models`), `VentaDiaria`/`VentaDiariaDetalle`/
  `PagoSuelto`/`EstadoVentaDiaria` (Task 1).

- [ ] **Step 1: Escribir el script**

`backend/scripts/import_peru_ventas_diarias.py`:

```python
"""
Importa el historico de SUPEROZONO PERU DIARIAS.xlsx (Enero-Julio 2026) al
tenant Peru. Uso unico — no idempotente entre corridas completas (correr
sobre una COPIA de la BD real primero, validar conteos, luego aplicar).

Uso: venv\\Scripts\\python.exe scripts\\import_peru_ventas_diarias.py <ruta.xlsx> <tenant_id>
"""
import sys
import asyncio
from pathlib import Path
from decimal import Decimal, InvalidOperation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import async_session  # noqa: E402
from app.core.tenancy import set_tenant_id, apply_rls_tenant, reset_tenant_id  # noqa: E402
from app.modules.ventas.models import Producto, Cliente  # noqa: E402
from app.modules.ventas_diarias.models import (  # noqa: E402
    VentaDiaria, VentaDiariaDetalle, PagoSuelto, EstadoVentaDiaria,
)

HOJAS_MESES = [
    "ENERO SUPEROZONO ", " FEBRERO  SUPEROZONO ", " MARZO  SUPEROZONO  ",
    "ABRIL SUPEROZONO ", "MAYO SUPEROZONO ", "JUNIO SUPEROZONO ",
    "JULIO SUPEROZONO ",
]

_ESTADO_MAP = {
    "ENTREGADO": EstadoVentaDiaria.ENTREGADO,
    "ENTREGDO": EstadoVentaDiaria.ENTREGADO,  # typo real observado en el Excel
    "DEVOLUCION": EstadoVentaDiaria.DEVOLUCION,
    "EN DESTINO": EstadoVentaDiaria.EN_DESTINO,
}


def _norm(v) -> str:
    return str(v or "").strip().upper()


def _to_decimal(v) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except InvalidOperation:
        return None


def _encontrar_header(ws) -> tuple[int, dict[str, int]]:
    """Busca la fila de encabezado (contiene 'FECHA') en las primeras 5 filas
    y devuelve (numero_de_fila, {clave_canonica: indice_columna})."""
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=5, values_only=True), start=1):
        if row and any(_norm(c) == "FECHA" for c in row):
            mapa: dict[str, int] = {}
            for idx, celda in enumerate(row):
                n = _norm(celda)
                if n == "FECHA":
                    mapa["fecha"] = idx
                elif n == "ASESOR":
                    mapa["asesor"] = idx
                elif n == "GUIA":
                    mapa["guia"] = idx
                elif n == "CODIGO":
                    mapa["codigo"] = idx
                elif n in ("CEDULA", "DNI"):
                    mapa["cedula"] = idx
                elif n == "CLIENTE":
                    mapa["cliente"] = idx
                elif n in ("PEDIDO", "PRODUCTO"):
                    mapa["producto"] = idx
                elif n.startswith("CANT"):
                    mapa["cantidad"] = idx
                elif n == "VENTA":
                    mapa["venta"] = idx
                elif n.startswith("RECAUDO 1"):
                    mapa["abono_1"] = idx
                elif n.startswith("RECAUDO 2"):
                    mapa["abono_2"] = idx
                elif n == "SALDO":
                    mapa["saldo"] = idx
                elif n == "ESTADO":
                    mapa["estado"] = idx
                elif n.startswith("PESOS"):
                    mapa["pesos_c"] = idx
                elif n.startswith("VALOR FLETE"):
                    mapa["valor_flete"] = idx
                elif n.startswith("COMO SE REALIZA"):
                    mapa["forma_pago"] = idx
            return i, mapa
    raise ValueError(f"No se encontro fila de encabezado en hoja '{ws.title}'")


async def _obtener_o_crear_producto(db, nombre: str, cache: dict[str, int]) -> int:
    nombre_norm = nombre.strip()
    if nombre_norm in cache:
        return cache[nombre_norm]
    sku = "PE-" + nombre_norm.upper().replace(" ", "-")[:20]
    existente = await db.scalar(select(Producto).where(Producto.sku == sku))
    if existente:
        cache[nombre_norm] = existente.id
        return existente.id
    producto = Producto(sku=sku, nombre=nombre_norm, marca="Super Ozono Peru")
    db.add(producto)
    await db.flush()
    cache[nombre_norm] = producto.id
    return producto.id


async def _obtener_o_crear_cliente(
    db, documento: str | None, nombre: str, cache: dict[str, int], contador: list[int]
) -> int:
    if not documento:
        contador[0] += 1
        documento = f"SIN-DOC-{contador[0]}"
    if documento in cache:
        return cache[documento]
    existente = await db.scalar(select(Cliente).where(Cliente.nit_cc == documento))
    if existente:
        cache[documento] = existente.id
        return existente.id
    cliente = Cliente(
        nit_cc=documento, razon_social=nombre.strip() or documento,
        tipo_persona="Natural",
    )
    db.add(cliente)
    await db.flush()
    cache[documento] = cliente.id
    return cliente.id


async def importar(xlsx_path: str, tenant_id: int) -> None:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    async with async_session() as db:
        set_tenant_id(tenant_id)
        await apply_rls_tenant(db, tenant_id)

        productos_cache: dict[str, int] = {}
        clientes_cache: dict[str, int] = {}
        contador_sin_doc = [0]
        total_ventas = 0
        total_pagos_sueltos = 0

        for nombre_hoja in HOJAS_MESES:
            if nombre_hoja not in wb.sheetnames:
                print(f"AVISO: hoja '{nombre_hoja}' no encontrada, se omite")
                continue
            ws = wb[nombre_hoja]
            header_row, col = _encontrar_header(ws)

            for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row, values_only=True):
                if not row or row[col["fecha"]] is None:
                    continue

                fecha = row[col["fecha"]]
                if hasattr(fecha, "date"):
                    fecha = fecha.date()

                cliente_nombre = row[col.get("cliente", -1)] if "cliente" in col else None
                producto_nombre = row[col.get("producto", -1)] if "producto" in col else None

                # Fila de "pago suelto": sin producto ni guia, cliente suele
                # empezar con "PAGO " — se importa como PagoSuelto, no como venta.
                if not producto_nombre and cliente_nombre and "PAGO" in _norm(cliente_nombre):
                    abono = _to_decimal(row[col["abono_1"]]) if "abono_1" in col else None
                    if abono:
                        db.add(PagoSuelto(
                            fecha=fecha,
                            cliente_texto=str(cliente_nombre).strip(),
                            monto=abono,
                            revisado=False,
                            notas="Importado de Excel — sin vinculo confirmado a una venta.",
                        ))
                        total_pagos_sueltos += 1
                    continue

                if not producto_nombre:
                    continue  # fila vacia / de total, sin producto real

                cliente_id = await _obtener_o_crear_cliente(
                    db,
                    str(row[col["cedula"]]).strip() if "cedula" in col and row[col["cedula"]] else None,
                    str(cliente_nombre or "Sin nombre"),
                    clientes_cache, contador_sin_doc,
                )
                producto_id = await _obtener_o_crear_producto(
                    db, str(producto_nombre), productos_cache)

                estado_raw = _norm(row[col["estado"]]) if "estado" in col else ""
                estado = _ESTADO_MAP.get(estado_raw, EstadoVentaDiaria.PENDIENTE)

                venta = VentaDiaria(
                    fecha=fecha,
                    asesor=str(row[col["asesor"]]).strip() if "asesor" in col and row[col["asesor"]] else None,
                    guia=str(row[col["guia"]]).strip() if "guia" in col and row[col["guia"]] else None,
                    codigo_guia=str(row[col["codigo"]]).strip() if "codigo" in col and row[col["codigo"]] else None,
                    cliente_id=cliente_id,
                    estado=estado,
                    forma_pago=str(row[col["forma_pago"]]).strip() if "forma_pago" in col and row[col["forma_pago"]] else None,
                    notas=f"Importado de hoja '{nombre_hoja}'",
                )
                db.add(venta)
                await db.flush()

                venta_val = _to_decimal(row[col["venta"]]) if "venta" in col else None
                abono_1 = _to_decimal(row[col["abono_1"]]) if "abono_1" in col else None
                abono_2 = _to_decimal(row[col["abono_2"]]) if "abono_2" in col else None
                saldo = (venta_val or Decimal("0")) - (abono_1 or Decimal("0")) - (abono_2 or Decimal("0"))

                db.add(VentaDiariaDetalle(
                    venta_diaria_id=venta.id,
                    producto_id=producto_id,
                    cantidad=_to_decimal(row[col["cantidad"]]) or Decimal("1"),
                    venta=venta_val,
                    abono_1=abono_1,
                    abono_2=abono_2,
                    saldo=saldo,
                    pesos_c=_to_decimal(row[col["pesos_c"]]) if "pesos_c" in col else None,
                    valor_flete=_to_decimal(row[col["valor_flete"]]) if "valor_flete" in col else None,
                ))
                total_ventas += 1

            print(f"Hoja '{nombre_hoja}': procesada.")

        await db.commit()
        reset_tenant_id()

    print(f"Importacion completa: {total_ventas} ventas diarias, {total_pagos_sueltos} pagos sueltos.")
    print("Revisar 'PESOS C' / 'VALOR FLETE' y los pagos sueltos con la auxiliar de Peru antes de usarlos en reportes.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: import_peru_ventas_diarias.py <ruta.xlsx> <tenant_id>")
    asyncio.run(importar(sys.argv[1], int(sys.argv[2])))
```

- [ ] **Step 2: Probar contra una copia de la base de datos, no la real**

```bash
cd backend
copy superozono.db superozono.db.backup-antes-import-peru
python scripts\import_peru_ventas_diarias.py "C:\Users\MI PC\Desktop\SUPEROZONO PERU DIARIAS.xlsx" 2
```

(usar el `tenant_id` real devuelto por el onboarding en Task 6, aquí se
asume `2`)

Expected: imprime "Hoja '...': procesada." por cada una de las 7 hojas y
al final "Importacion completa: N ventas diarias, M pagos sueltos."

- [ ] **Step 3: Validar conteos contra lo esperado**

Run:
```bash
python -c "
import asyncio
from sqlalchemy import select, func
from app.core.database import async_session
from app.core.tenancy import set_tenant_id, apply_rls_tenant
from app.modules.ventas_diarias.models import VentaDiaria

async def main():
    async with async_session() as db:
        set_tenant_id(2)
        await apply_rls_tenant(db, 2)
        total = await db.scalar(select(func.count(VentaDiaria.id)))
        print('Total ventas diarias importadas:', total)

asyncio.run(main())
"
```

Expected: un total cercano a 944 (120+123+73+76+189+182+181, la suma de
filas con venta real detectadas en el análisis previo — puede variar
levemente por filas ambiguas).

- [ ] **Step 4: Solo si los conteos cuadran, correr contra la base real (sin la copia) y avisar a la auxiliar de Perú para que deje de usar el Excel**

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/import_peru_ventas_diarias.py
git commit -m "feat(ventas-diarias): script de importacion del historico de Peru"
```

---

### Task 8: Frontend — servicio API + vista + integración de rutas/menú

**Files:**
- Create: `frontend/src/services/ventasDiariasApi.ts`
- Create: `frontend/src/views/VentasDiariasView.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

**Interfaces:**
- Consumes: `api` (axios instance, `frontend/src/services/api.ts`),
  endpoints de Task 3.
- Produces: `ventasDiariasApi.{list, create, resumenMensual}`,
  componente `VentasDiariasView`, `ViewId` `'ventas-diarias'`.

- [ ] **Step 1: Servicio API**

`frontend/src/services/ventasDiariasApi.ts`:

```typescript
/**
 * Super Ozono Global — API Service para Ventas Diarias (Run 6)
 */
import { api } from './api';

const BASE = '/v1/ventas-diarias';

// Los campos Decimal del backend viajan como string en el JSON (igual que
// Producto.precio_venta en ventasApi.ts) — usar Number(...) antes de sumar.
export interface VentaDiariaDetalle {
  id: number;
  producto_id: number;
  cantidad: string;
  venta?: string;
  abono_1?: string;
  abono_2?: string;
  saldo: string;
  pesos_c?: string;
  valor_flete?: string;
}

export interface VentaDiariaDetalleInput {
  producto_id: number;
  cantidad: number;
  venta?: number;
  abono_1?: number;
  abono_2?: number;
}

export interface VentaDiaria {
  id: number;
  fecha: string;
  asesor?: string;
  guia?: string;
  codigo_guia?: string;
  cliente_id: number;
  estado: string;
  forma_pago?: string;
  notas?: string;
  detalles: VentaDiariaDetalle[];
}

export interface VentaDiariaInput {
  fecha: string;
  asesor?: string;
  guia?: string;
  codigo_guia?: string;
  cliente_id: number;
  estado: string;
  forma_pago?: string;
  notas?: string;
  detalles: VentaDiariaDetalleInput[];
}

export interface ResumenMensual {
  anio: number;
  mes: number;
  total_venta: string;
  total_abonado: string;
  total_saldo: string;
  cantidad_entregado: number;
  cantidad_devolucion: number;
}

export const ventasDiariasApi = {
  list: (params?: { fecha_desde?: string; fecha_hasta?: string; estado?: string; asesor?: string }) =>
    api.get<VentaDiaria[]>(`${BASE}/`, { params }),

  get: (id: number) => api.get<VentaDiaria>(`${BASE}/${id}`),

  create: (data: VentaDiariaInput) => api.post<VentaDiaria>(`${BASE}/`, data),

  resumenMensual: (anio: number, mes: number) =>
    api.get<ResumenMensual>(`${BASE}/resumen/${anio}/${mes}`),
};
```

- [ ] **Step 2: Vista**

`frontend/src/views/VentasDiariasView.tsx`:

```tsx
/**
 * Ventas Diarias View — Peru/Ecuador: contraentrega por guia
 */
import { useState, useEffect, useCallback } from 'react';
import { ventasDiariasApi, type VentaDiaria, type ResumenMensual } from '../services/ventasDiariasApi';
import { ventasApi, type Producto, type Cliente } from '../services/ventasApi';
import Toast from '../components/Toast';
import ErrorState from '../components/ErrorState';

const ESTADOS = ['Pendiente', 'Entregado', 'En destino', 'Devolución'];

export default function VentasDiariasView() {
  const [ventas, setVentas] = useState<VentaDiaria[]>([]);
  const [resumen, setResumen] = useState<ResumenMensual | null>(null);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [mostrarForm, setMostrarForm] = useState(false);

  const hoy = new Date();
  const [anio] = useState(hoy.getFullYear());
  const [mes] = useState(hoy.getMonth() + 1);

  const cargar = useCallback(() => {
    setLoading(true);
    setError(false);
    Promise.all([
      ventasDiariasApi.list(filtroEstado ? { estado: filtroEstado } : undefined),
      ventasDiariasApi.resumenMensual(anio, mes),
      ventasApi.getProductos(),
      ventasApi.getClientes(),
    ])
      .then(([v, r, p, c]) => {
        setVentas(v.data);
        setResumen(r.data);
        setProductos(p.data);
        setClientes(c.data);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [filtroEstado, anio, mes]);

  useEffect(() => { cargar(); }, [cargar]);

  const crearVentaRapida = async (form: {
    fecha: string; asesor: string; guia: string; cliente_id: number;
    producto_id: number; cantidad: number; venta: number; abono_1: number; estado: string;
  }) => {
    try {
      await ventasDiariasApi.create({
        fecha: form.fecha,
        asesor: form.asesor || undefined,
        guia: form.guia || undefined,
        cliente_id: form.cliente_id,
        estado: form.estado,
        detalles: [{
          producto_id: form.producto_id,
          cantidad: form.cantidad,
          venta: form.venta,
          abono_1: form.abono_1 || undefined,
        }],
      });
      setToast({ message: 'Venta diaria registrada', type: 'success' });
      setMostrarForm(false);
      cargar();
    } catch {
      setToast({ message: 'Error al registrar la venta diaria', type: 'error' });
    }
  };

  if (loading) return <div className="empty-state fade-in"><div className="empty-state-text">Cargando ventas diarias...</div></div>;
  if (error) return <ErrorState mensaje="Error al cargar ventas diarias" onRetry={cargar} />;

  return (
    <div className="fade-in">
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      {resumen && (
        <div className="kpi-row">
          <div className="kpi-tile"><span>Venta del mes</span><strong>{resumen.total_venta}</strong></div>
          <div className="kpi-tile"><span>Recaudado</span><strong>{resumen.total_abonado}</strong></div>
          <div className="kpi-tile"><span>Saldo pendiente</span><strong>{resumen.total_saldo}</strong></div>
          <div className="kpi-tile"><span>Entregados</span><strong>{resumen.cantidad_entregado}</strong></div>
          <div className="kpi-tile"><span>Devoluciones</span><strong>{resumen.cantidad_devolucion}</strong></div>
        </div>
      )}

      <div className="toolbar">
        <select value={filtroEstado} onChange={e => setFiltroEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        <button onClick={() => setMostrarForm(true)}>+ Nueva venta diaria</button>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Fecha</th><th>Asesor</th><th>Guía</th><th>Cliente</th>
            <th>Producto</th><th>Venta</th><th>Saldo</th><th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {ventas.map(v => (
            <tr key={v.id}>
              <td>{v.fecha}</td>
              <td>{v.asesor}</td>
              <td>{v.guia}</td>
              <td>{clientes.find(c => c.id === v.cliente_id)?.razon_social ?? v.cliente_id}</td>
              <td>{v.detalles.map(d => productos.find(p => p.id === d.producto_id)?.nombre ?? d.producto_id).join(', ')}</td>
              <td>{v.detalles.reduce((acc, d) => acc + Number(d.venta ?? 0), 0)}</td>
              <td>{v.detalles.reduce((acc, d) => acc + Number(d.saldo), 0)}</td>
              <td>{v.estado}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {mostrarForm && (
        <VentaDiariaForm
          productos={productos}
          clientes={clientes}
          onCancel={() => setMostrarForm(false)}
          onSubmit={crearVentaRapida}
        />
      )}
    </div>
  );
}

function VentaDiariaForm({ productos, clientes, onCancel, onSubmit }: {
  productos: Producto[];
  clientes: Cliente[];
  onCancel: () => void;
  onSubmit: (form: {
    fecha: string; asesor: string; guia: string; cliente_id: number;
    producto_id: number; cantidad: number; venta: number; abono_1: number; estado: string;
  }) => void;
}) {
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [asesor, setAsesor] = useState('');
  const [guia, setGuia] = useState('');
  const [clienteId, setClienteId] = useState(clientes[0]?.id ?? 0);
  const [productoId, setProductoId] = useState(productos[0]?.id ?? 0);
  const [cantidad, setCantidad] = useState(1);
  const [venta, setVenta] = useState(0);
  const [abono1, setAbono1] = useState(0);
  const [estado, setEstado] = useState('Pendiente');

  const saldo = venta - abono1;

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>Nueva venta diaria</h3>
        <label>Fecha <input type="date" value={fecha} onChange={e => setFecha(e.target.value)} /></label>
        <label>Asesor <input value={asesor} onChange={e => setAsesor(e.target.value)} /></label>
        <label>Guía <input value={guia} onChange={e => setGuia(e.target.value)} /></label>
        <label>Cliente
          <select value={clienteId} onChange={e => setClienteId(Number(e.target.value))}>
            {clientes.map(c => <option key={c.id} value={c.id}>{c.razon_social}</option>)}
          </select>
        </label>
        <label>Producto
          <select value={productoId} onChange={e => setProductoId(Number(e.target.value))}>
            {productos.map(p => <option key={p.id} value={p.id}>{p.nombre}</option>)}
          </select>
        </label>
        <label>Cantidad <input type="number" value={cantidad} onChange={e => setCantidad(Number(e.target.value))} /></label>
        <label>Venta <input type="number" value={venta} onChange={e => setVenta(Number(e.target.value))} /></label>
        <label>Abono <input type="number" value={abono1} onChange={e => setAbono1(Number(e.target.value))} /></label>
        <div>Saldo calculado: {saldo}</div>
        <label>Estado
          <select value={estado} onChange={e => setEstado(e.target.value)}>
            {ESTADOS_FORM.map(e => <option key={e} value={e}>{e}</option>)}
          </select>
        </label>
        <div className="modal-actions">
          <button onClick={onCancel}>Cancelar</button>
          <button onClick={() => onSubmit({
            fecha, asesor, guia, cliente_id: clienteId, producto_id: productoId,
            cantidad, venta, abono_1: abono1, estado,
          })}>Guardar</button>
        </div>
      </div>
    </div>
  );
}

const ESTADOS_FORM = ['Pendiente', 'Entregado', 'En destino', 'Devolución'];
```

- [ ] **Step 3: Registrar la vista en `App.tsx`**

Agregar al `ViewId`:

```typescript
export type ViewId =
  | 'dashboard'
  | 'puc'
  | 'ventas-diarias'
  | 'centros-costo'
  ...
```

Agregar el lazy import:

```typescript
const VentasDiariasView = lazy(() => import('./views/VentasDiariasView'))
```

Agregar la entrada en `VIEW_TITLES` (es `Record<ViewId, string>` — TypeScript
no compila si falta una clave del union `ViewId`):

```typescript
  'ventas-diarias': 'Ventas Diarias (Perú)',
```

Agregar a `ROLE_VIEWS` para `Superusuario`, `Directora`, `CEO`,
`Auxiliar Contable` (los roles que ya ven `'ventas'`), agregando
`'ventas-diarias'` junto a `'ventas'` en cada lista.

Agregar el case en `renderView()`:

```typescript
      case 'ventas-diarias':
        return <VentasDiariasView />
```

- [ ] **Step 4: Registrar el ítem de menú en `Sidebar.tsx`**

En `NAV_SECTIONS`, sección `Operaciones`, junto al ítem `'ventas'`:

```typescript
      { id: 'ventas-diarias' as ViewId, icon: '🌎', label: 'Ventas Diarias (Perú)' },
```

- [ ] **Step 5: Verificar que compila**

Run: `cd frontend && npm run build`
Expected: build exitoso, sin errores de TypeScript.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/services/ventasDiariasApi.ts frontend/src/views/VentasDiariasView.tsx frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "feat(ventas-diarias): vista, servicio API y menu en frontend"
```

---

### Task 9: Verificación end-to-end en navegador real

**Files:** ninguno (verificación manual, sin cambios de código salvo
posibles fixes que surjan).

- [ ] **Step 1: Instalar Playwright temporalmente (si no está)**

Run: `cd frontend && npm install -D @playwright/test && npx playwright install chromium`

- [ ] **Step 2: Login como auxiliar de Perú y crear una venta diaria**

Abrir el ERP en la LAN (`https://192.168.1.131:5173` o el que corresponda),
loguearse con `auxiliar.peru@superozonoglobal.com`, entrar a "Ventas
Diarias (Perú)", crear una venta con los datos de prueba de Task 4, y
confirmar que aparece en la tabla y en el resumen del mes.

- [ ] **Step 3: Confirmar aislamiento — login como usuario de Colombia**

Cerrar sesión, loguearse como un usuario de Colombia (Superusuario o
Auxiliar Contable existente), entrar a "Ventas Diarias (Perú)" (si el rol
lo permite) o al módulo "Ventas" de Colombia, y confirmar que **no** ve la
venta diaria creada para Perú, y viceversa: la auxiliar de Perú no ve
facturas de Colombia.

- [ ] **Step 4: Desinstalar Playwright**

Run: `cd frontend && npm uninstall @playwright/test`

- [ ] **Step 5: Registrar el resultado de la verificación en BITACORA.md**

Agregar a la entrada de la sesión: "Verificado en navegador real: login
auxiliar Perú → crear venta diaria → confirmado aislamiento cruzado con
Colombia (2026-07-23)."

---

## Spec Coverage Checklist (autorrevisión)

- Arquitectura (activar tenancy en LAN/SQLite, sin nube) → Task 6.
- Modelo de datos nuevo (`VentaDiaria`/`VentaDiariaDetalle`, abono/saldo
  por línea) → Task 1.
- Reutilización de `Producto`/`Cliente` por tenant → Tasks 3, 7.
- Importación del histórico (7 hojas, filas de pago suelto, columnas
  ambiguas) → Task 7.
- Captura en vivo (UI, saldo autocalculado, totales del mes) → Task 8.
- Verificación con navegador real para cambios de auth/tenant → Task 9.
- Aislamiento por tenant a nivel de aplicación (no solo RLS) → Tasks 3, 5.
- Preguntas abiertas para la auxiliar de Perú (VALOR FLETE, pagos sueltos)
  → documentadas en el script de import (Task 7) y quedan en `PagoSuelto`
  con `revisado=False` para seguimiento, no bloquean el desarrollo.
