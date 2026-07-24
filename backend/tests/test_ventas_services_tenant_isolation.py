"""Auditoria de aislamiento cross-tenant — app/modules/ventas/services.py
(2026-07-24).

Encontrado en la revision final de la rama fix-cross-tenant-audit:
confirmar_venta/anular_venta (los 3 endpoints que originaron toda la
auditoria en la revision de Run 6) en realidad delegan en este archivo de
servicio, que nunca fue tocado. Tiene el mismo patron de queries sin scope
que ya se corrigio en los routers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    apply_rls_tenant,
    reset_tenant_id,
    set_tenant_id,
)
from app.modules.contabilidad.models import CuentaPorCobrar, EstadoDocumento
from app.modules.ventas.models import Cliente, EstadoVenta, Producto, VentaDetalle, VentaDocumento
from app.modules.ventas.services import anular_venta, confirmar_venta


@dataclass
class _Usuario:
    id: int = 1


async def _en_tenant2(db_session):
    existing = await db_session.get(Tenant, 2)
    if not existing:
        db_session.add(Tenant(id=2, codigo="vs-test", razon_social="VS Test", activo=True))
        await db_session.flush()
    set_tenant_id(2)
    await apply_rls_tenant(db_session, 2)


async def _al_tenant_default(db_session):
    reset_tenant_id()
    await apply_rls_tenant(db_session, DEFAULT_TENANT_ID)


@pytest.mark.asyncio
async def test_confirmar_venta_no_reutiliza_cxc_de_otro_tenant(db_session):
    """CuentaPorCobrar.numero_factura es unique=True GLOBAL (gap de esquema
    ya documentado) pero VentaDocumento.numero NO tiene ninguna restriccion
    — dos tenants pueden tener ventas con el mismo numero. Antes del fix,
    confirmar_venta del tenant 1 encontraba la CxC del tenant 2 (mismo
    numero_factura), la trataba como "ya existe" y NUNCA creaba la propia:
    la venta del tenant 1 quedaba sin CxC, silenciosamente enlazada a la
    cartera de otro tenant."""
    await _en_tenant2(db_session)
    db_session.add(CuentaPorCobrar(
        numero_factura="COLISION-FACT-001", fecha_emision=date(2026, 1, 1),
        cliente_nit="T2", valor_factura=Decimal("999999"), tenant_id=2,
    ))
    await db_session.commit()
    await _al_tenant_default(db_session)

    cliente = Cliente(nit_cc="T1-VS-CLI", razon_social="Cliente T1", tenant_id=DEFAULT_TENANT_ID)
    producto = Producto(
        sku="T1-VS-PROD", nombre="Producto T1", marca="X",
        precio_venta=Decimal("100"), stock_actual=Decimal("10"), tenant_id=DEFAULT_TENANT_ID,
    )
    db_session.add_all([cliente, producto])
    await db_session.flush()
    venta = VentaDocumento(
        numero="COLISION-FACT-001", fecha=date(2026, 1, 1), cliente_id=cliente.id,
        total=Decimal("100"), estado=EstadoVenta.BORRADOR, tenant_id=DEFAULT_TENANT_ID,
    )
    db_session.add(venta)
    await db_session.flush()
    db_session.add(VentaDetalle(
        venta_id=venta.id, producto_id=producto.id, cantidad=Decimal("1"),
        precio_unitario=Decimal("100"), total_linea=Decimal("100"), tenant_id=DEFAULT_TENANT_ID,
    ))
    await db_session.commit()

    try:
        await confirmar_venta(db_session, venta, _Usuario())
        await db_session.commit()
    except IntegrityError:
        # Esperado hasta la migracion del constraint compuesto (mismo gap
        # que PlanCuentas.codigo_puc) — lo importante es que NO reutilizo
        # silenciosamente la CxC del tenant 2.
        await db_session.rollback()
        return

    cxc_propia = await db_session.scalar(
        select(CuentaPorCobrar).where(
            CuentaPorCobrar.numero_factura == "COLISION-FACT-001",
            CuentaPorCobrar.tenant_id == DEFAULT_TENANT_ID,
        )
    )
    assert cxc_propia is not None, "el tenant 1 debe tener su PROPIA CxC, no reusar la del tenant 2"


@pytest.mark.asyncio
async def test_confirmar_venta_stock_no_usa_producto_de_otro_tenant(db_session):
    """El chequeo de stock de confirmar_venta cargaba los Producto por id sin
    filtrar por tenant (with_for_update). Si una VentaDetalle terminara
    referenciando el id de un producto de OTRO tenant (defensa en
    profundidad — no deberia poder pasar por las validaciones ya corregidas
    en create_venta, pero este archivo nunca validaba nada por su cuenta),
    confirmar_venta no debe usar el stock de ese producto ajeno para decidir
    si hay existencia suficiente."""
    await _en_tenant2(db_session)
    producto_t2 = Producto(
        sku="T2-VS-PROD", nombre="Producto T2", marca="X",
        precio_venta=Decimal("100"), stock_actual=Decimal("999"), tenant_id=2,
    )
    db_session.add(producto_t2)
    await db_session.commit()
    await db_session.refresh(producto_t2)
    producto_t2_id = producto_t2.id
    await _al_tenant_default(db_session)

    cliente = Cliente(nit_cc="T1-VS-CLI2", razon_social="Cliente T1", tenant_id=DEFAULT_TENANT_ID)
    db_session.add(cliente)
    await db_session.flush()
    venta = VentaDocumento(
        numero="T1-VS-V0002", fecha=date(2026, 1, 1), cliente_id=cliente.id,
        total=Decimal("100"), estado=EstadoVenta.BORRADOR, tenant_id=DEFAULT_TENANT_ID,
    )
    db_session.add(venta)
    await db_session.flush()
    # Detalle "envenenado": referencia un producto que pertenece al tenant 2.
    db_session.add(VentaDetalle(
        venta_id=venta.id, producto_id=producto_t2_id, cantidad=Decimal("1"),
        precio_unitario=Decimal("100"), total_linea=Decimal("100"), tenant_id=DEFAULT_TENANT_ID,
    ))
    await db_session.commit()

    from app.modules.ventas.services import VentaError
    with pytest.raises(VentaError):
        await confirmar_venta(db_session, venta, _Usuario())


@pytest.mark.asyncio
async def test_anular_venta_no_toca_cxc_de_otro_tenant(db_session):
    await _en_tenant2(db_session)
    cxc_t2 = CuentaPorCobrar(
        numero_factura="COLISION-FACT-002", fecha_emision=date(2026, 1, 1),
        cliente_nit="T2", valor_factura=Decimal("100"), abonos=Decimal("50"),
        estado=EstadoDocumento.PARCIAL, tenant_id=2,
    )
    db_session.add(cxc_t2)
    await db_session.commit()
    await db_session.refresh(cxc_t2)
    await _al_tenant_default(db_session)

    cliente = Cliente(nit_cc="T1-VS-CLI3", razon_social="Cliente T1", tenant_id=DEFAULT_TENANT_ID)
    db_session.add(cliente)
    await db_session.flush()
    venta = VentaDocumento(
        numero="COLISION-FACT-002", fecha=date(2026, 1, 1), cliente_id=cliente.id,
        total=Decimal("100"), estado=EstadoVenta.CONFIRMADA, tenant_id=DEFAULT_TENANT_ID,
    )
    db_session.add(venta)
    await db_session.commit()

    # Antes del fix: encontraba la CxC (con abonos) del tenant 2 y bloqueaba
    # la anulacion pensando que era la propia -- o peor, la marcaba anulada.
    await anular_venta(db_session, venta, _Usuario())
    await db_session.commit()

    await _en_tenant2(db_session)
    otra = await db_session.get(CuentaPorCobrar, cxc_t2.id)
    assert otra.estado == EstadoDocumento.PARCIAL, "la CxC del tenant 2 no debe verse afectada"
    await _al_tenant_default(db_session)
