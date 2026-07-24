"""Auditoria de aislamiento cross-tenant — motor de asientos contables,
app/modules/contabilidad/asientos.py (2026-07-24).

Encontrado en la revision final de la rama fix-cross-tenant-audit: este
archivo SI fue tocado por la auditoria (2 lookups de Cliente por FK ya se
habian corregido) pero tres funciones internas del motor se quedaron sin
scope — el peor hallazgo de toda la auditoria, porque una de ellas
(reversar_asientos) es una ESCRITURA, no solo una lectura.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    apply_rls_tenant,
    reset_tenant_id,
    set_tenant_id,
)
from app.modules.contabilidad.asientos import (
    _get_or_create_cuenta,
    _periodo_para,
    reversar_asientos,
    validar_periodo_abierto,
)
from app.modules.contabilidad.models import (
    AsientoContable,
    ClaseCuenta,
    EstadoPeriodo,
    MovimientoAsiento,
    NaturalezaCuenta,
    PeriodoContable,
    PlanCuentas,
)


async def _en_tenant2(db_session):
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="asi-test", razon_social="Asi Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)


async def _al_tenant_default(db_session):
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)


@pytest.mark.asyncio
async def test_get_or_create_cuenta_no_reutiliza_cuenta_de_otro_tenant(db_session):
    """_get_or_create_cuenta no debe devolver silenciosamente la cuenta de
    OTRO tenant solo porque el codigo_puc coincide. Nota: PlanCuentas.codigo_puc
    es unique=True a nivel de esquema (gap ya documentado, ver
    test_contabilidad_tenant_isolation.py) — el tenant 1 intentando crear la
    MISMA cuenta que ya existe para el tenant 2 puede fallar con
    IntegrityError en vez de tener exito; lo que este test prueba es que NUNCA
    reutiliza silenciosamente la fila ajena (ni exito con datos cruzados)."""
    await _en_tenant2(db_session)
    db_session.add(PlanCuentas(
        codigo_puc="417501", nombre="Devoluciones en ventas",
        clase=ClaseCuenta.INGRESO, naturaleza=NaturalezaCuenta.DEBITO, tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    try:
        cuenta = await _get_or_create_cuenta(db_session, "417501")
    except IntegrityError:
        await db_session.rollback()
        return  # esperado hasta la migracion del constraint compuesto; no hubo reuso silencioso
    assert cuenta.tenant_id == DEFAULT_TENANT_ID


@pytest.mark.asyncio
async def test_validar_periodo_abierto_no_bloquea_por_cierre_de_otro_tenant(db_session):
    await _en_tenant2(db_session)
    db_session.add(PeriodoContable(
        anio=2026, mes=6, periodo="2026-06", estado=EstadoPeriodo.CERRADO, tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    # No debe lanzar: el tenant 1 no tiene periodo propio para 2026-06, asi
    # que el cierre del tenant 2 no le aplica.
    await validar_periodo_abierto(db_session, date(2026, 6, 15))


@pytest.mark.asyncio
async def test_periodo_para_no_devuelve_periodo_de_otro_tenant(db_session):
    await _en_tenant2(db_session)
    periodo = PeriodoContable(anio=2026, mes=6, periodo="2026-06", tenant_id=2)
    db_session.add(periodo)
    await db_session.commit()
    await _al_tenant_default(db_session)

    resultado = await _periodo_para(db_session, date(2026, 6, 15))
    assert resultado is None


@pytest.mark.asyncio
async def test_reversar_asientos_no_reversa_asiento_de_otro_tenant(db_session):
    """El caso mas grave: dos asientos con el MISMO documento_ref en tenants
    distintos (VentaDocumento.numero no tiene ninguna restriccion de
    unicidad, ni siquiera global). reversar_asientos no debe tocar el del
    otro tenant."""
    await _en_tenant2(db_session)
    cuenta_t2 = PlanCuentas(
        codigo_puc="T2-110505", nombre="Caja T2",
        clase=ClaseCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEBITO, tenant_id=2,
    )
    db_session.add(cuenta_t2)
    await db_session.flush()
    asiento_t2 = AsientoContable(
        fecha=date(2026, 1, 1), descripcion="Venta T2", documento_ref="COLISION-001", tenant_id=2,
    )
    db_session.add(asiento_t2)
    await db_session.flush()
    db_session.add(MovimientoAsiento(
        asiento_id=asiento_t2.id, cuenta_id=cuenta_t2.id,
        debito=Decimal("100"), credito=Decimal("0"), tenant_id=2,
    ))
    await db_session.commit()
    await db_session.refresh(asiento_t2)
    asiento_t2_id = asiento_t2.id
    await _al_tenant_default(db_session)

    cuenta_t1 = PlanCuentas(
        codigo_puc="T1-110505", nombre="Caja T1",
        clase=ClaseCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEBITO, tenant_id=DEFAULT_TENANT_ID,
    )
    db_session.add(cuenta_t1)
    await db_session.flush()
    asiento_t1 = AsientoContable(
        fecha=date(2026, 1, 1), descripcion="Venta T1", documento_ref="COLISION-001",
        tenant_id=DEFAULT_TENANT_ID,
    )
    db_session.add(asiento_t1)
    await db_session.flush()
    db_session.add(MovimientoAsiento(
        asiento_id=asiento_t1.id, cuenta_id=cuenta_t1.id,
        debito=Decimal("50"), credito=Decimal("0"),
        tenant_id=DEFAULT_TENANT_ID,
    ))
    await db_session.commit()

    reversos = await reversar_asientos(
        db_session, documento_ref="COLISION-001", usuario_id=None, motivo="test"
    )
    await db_session.commit()

    assert len(reversos) == 1
    assert reversos[0].tenant_id == DEFAULT_TENANT_ID

    await db_session.refresh(asiento_t1)
    assert asiento_t1.reversado is True

    await _en_tenant2(db_session)
    otro = await db_session.get(AsientoContable, asiento_t2_id)
    assert otro.reversado is False
    await _al_tenant_default(db_session)
