"""
Motor de asientos contables — partida doble automática.

Genera un AsientoContable (cabecera) + MovimientoAsiento (débitos/créditos)
al confirmar ventas y compras y al registrar abonos de cartera, y el asiento
de reverso al anular.

⚠️ MAPEO PUC BORRADOR — validar con el contador antes de usar los asientos
para reportes oficiales. Los códigos siguen el estándar del Decreto 2650:

    Ventas:   DB 130505 Clientes         (total a cobrar)
              DB 135515/17/18 Retenciones que nos practicaron
              CR 413595 Ingresos por ventas (base gravable)
              CR 240801 IVA generado

    Compras:  DB 143501 Inventario de mercancías (base gravable)
              DB 240802 IVA descontable
              CR 220501 Proveedores nacionales (total a pagar)
              CR 236540/236701/236801 Retenciones que practicamos

    Abono CxC (Recibo de Caja):        DB 110505 Caja  / CR 130505 Clientes
    Abono CxP (Comprobante de Egreso): DB 220501 Proveedores / CR 110505 Caja

Si una cuenta del mapeo no existe en el PUC, el motor la crea automáticamente
(la empresa puede renombrarla después) — así el asiento nunca queda a medias.
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contabilidad.models import (
    AsientoContable, MovimientoAsiento, PlanCuentas, PeriodoContable,
    Tercero, TipoTercero, EstadoPeriodo,
    ClaseCuenta, NaturalezaCuenta, NivelCuenta,
)

# ── Catálogo de cuentas usadas por el motor ───────────────
# codigo → (nombre, clase, naturaleza)
CUENTAS_MOTOR: dict[str, tuple[str, ClaseCuenta, NaturalezaCuenta]] = {
    "110505": ("Caja general", ClaseCuenta.ACTIVO, NaturalezaCuenta.DEBITO),
    "130505": ("Clientes nacionales", ClaseCuenta.ACTIVO, NaturalezaCuenta.DEBITO),
    "135515": ("Retención en la fuente a favor", ClaseCuenta.ACTIVO, NaturalezaCuenta.DEBITO),
    "135517": ("ReteIVA a favor", ClaseCuenta.ACTIVO, NaturalezaCuenta.DEBITO),
    "135518": ("ReteICA a favor", ClaseCuenta.ACTIVO, NaturalezaCuenta.DEBITO),
    "143501": ("Inventario de mercancías", ClaseCuenta.ACTIVO, NaturalezaCuenta.DEBITO),
    "220501": ("Proveedores nacionales", ClaseCuenta.PASIVO, NaturalezaCuenta.CREDITO),
    "236540": ("Retención en la fuente practicada", ClaseCuenta.PASIVO, NaturalezaCuenta.CREDITO),
    "236701": ("ReteIVA practicado", ClaseCuenta.PASIVO, NaturalezaCuenta.CREDITO),
    "236801": ("ReteICA practicado", ClaseCuenta.PASIVO, NaturalezaCuenta.CREDITO),
    "240801": ("IVA generado en ventas", ClaseCuenta.PASIVO, NaturalezaCuenta.CREDITO),
    "240802": ("IVA descontable en compras", ClaseCuenta.PASIVO, NaturalezaCuenta.CREDITO),
    "413595": ("Ingresos por ventas de productos", ClaseCuenta.INGRESO, NaturalezaCuenta.CREDITO),
    # Contra-ingreso: naturaleza debito dentro de la clase Ingreso — resta del P&L
    "417501": ("Devoluciones en ventas", ClaseCuenta.INGRESO, NaturalezaCuenta.DEBITO),
}

CERO = Decimal("0.00")


async def _get_or_create_cuenta(db: AsyncSession, codigo: str) -> PlanCuentas:
    cuenta = await db.scalar(select(PlanCuentas).where(PlanCuentas.codigo_puc == codigo))
    if cuenta:
        return cuenta
    nombre, clase, naturaleza = CUENTAS_MOTOR[codigo]
    cuenta = PlanCuentas(
        codigo_puc=codigo,
        nombre=nombre,
        clase=clase,
        naturaleza=naturaleza,
        nivel=NivelCuenta.AUXILIAR,
    )
    db.add(cuenta)
    await db.flush()
    return cuenta


async def _get_or_create_tercero(
    db: AsyncSession, nit: str | None, razon_social: str | None, tipo: TipoTercero
) -> int | None:
    """
    Materializa progresivamente el registro único de terceros: cada cliente o
    proveedor que participa en un asiento queda creado/vinculado en `terceros`
    por su NIT — habilita el auxiliar contable por tercero.
    """
    if not nit:
        return None
    tercero = await db.scalar(select(Tercero).where(Tercero.nit_cc == nit))
    if tercero:
        # Un NIT que ya era Cliente y ahora aparece como Proveedor (o viceversa) es Mixto
        if tercero.tipo != tipo and tercero.tipo != TipoTercero.MIXTO:
            tercero.tipo = TipoTercero.MIXTO
        return tercero.id
    tercero = Tercero(nit_cc=nit, razon_social=razon_social or nit, tipo=tipo)
    db.add(tercero)
    await db.flush()
    return tercero.id


async def validar_periodo_abierto(db: AsyncSession, fecha) -> None:
    """
    Cierre contable real: si existe un PeriodoContable CERRADO para el mes de
    `fecha`, ninguna operación de negocio (confirmar/anular documentos, abonar
    o anular pagos) puede registrar movimientos ahí. Si el mes no tiene período
    creado, se permite (la empresa no crea períodos por adelantado).
    """
    periodo = await db.scalar(
        select(PeriodoContable).where(
            PeriodoContable.anio == fecha.year, PeriodoContable.mes == fecha.month
        )
    )
    if periodo and periodo.estado == EstadoPeriodo.CERRADO:
        raise HTTPException(
            400,
            f"El período contable {periodo.periodo} está CERRADO. "
            "Reábrelo en Contabilidad → Períodos para registrar movimientos en esa fecha.",
        )


async def _periodo_para(db: AsyncSession, fecha) -> int | None:
    periodo = await db.scalar(
        select(PeriodoContable).where(
            PeriodoContable.anio == fecha.year, PeriodoContable.mes == fecha.month
        )
    )
    return periodo.id if periodo else None


async def registrar_asiento(
    db: AsyncSession,
    *,
    fecha,
    descripcion: str,
    tipo_documento: str,
    modulo_origen: str,
    documento_ref: str,
    usuario_id: int | None,
    lineas: list[tuple[str, Decimal, Decimal]],
    centro_costo_id: int | None = None,
    tercero_id: int | None = None,
) -> AsientoContable:
    """
    Crea el asiento con sus movimientos. `lineas` = [(codigo_puc, debito, credito)].
    Valida partida doble: la suma de débitos debe igualar la de créditos.
    Las líneas en cero se omiten.
    """
    # Punto único de control: TODO movimiento contable pasa por aquí.
    # Si el período del mes está cerrado, la operación completa se aborta
    # (el rollback de la sesión revierte stock/cartera creados antes).
    await validar_periodo_abierto(db, fecha)

    lineas = [(c, d, cr) for c, d, cr in lineas if d > CERO or cr > CERO]
    total_debito = sum(d for _, d, _ in lineas)
    total_credito = sum(c for _, _, c in lineas)
    if total_debito != total_credito:
        raise ValueError(
            f"Asiento descuadrado para {documento_ref}: "
            f"débitos {total_debito} != créditos {total_credito}"
        )

    asiento = AsientoContable(
        fecha=fecha,
        descripcion=descripcion,
        tipo_documento=tipo_documento,
        modulo_origen=modulo_origen,
        documento_ref=documento_ref,
        usuario_id=usuario_id,
        periodo_id=await _periodo_para(db, fecha),
    )
    db.add(asiento)
    await db.flush()

    for codigo, debito, credito in lineas:
        cuenta = await _get_or_create_cuenta(db, codigo)
        db.add(MovimientoAsiento(
            asiento_id=asiento.id,
            cuenta_id=cuenta.id,
            tercero_id=tercero_id,
            centro_costo_id=centro_costo_id,
            debito=debito,
            credito=credito,
        ))
    await db.flush()
    return asiento


async def reversar_asientos(
    db: AsyncSession, *, documento_ref: str, usuario_id: int | None, motivo: str
) -> list[AsientoContable]:
    """
    Reverso por anulación: por cada asiento del documento crea un asiento
    espejo (débitos ↔ créditos). Ambos quedan ACTIVOS y se netean a cero en
    cualquier agregación — nunca se ocultan movimientos (traza de auditoría).
    El flag `reversado` en el original evita generar el reverso dos veces.
    """
    asientos = (await db.execute(
        select(AsientoContable).where(
            AsientoContable.documento_ref == documento_ref,
            AsientoContable.reversado.is_(False),
            AsientoContable.descripcion.notlike("REVERSO%"),
        )
    )).scalars().all()

    reversos = []
    for original in asientos:
        # El reverso se registra en la fecha del original: si ese mes ya se
        # cerró, la anulación exige reabrir el período (decisión del contador)
        await validar_periodo_abierto(db, original.fecha)
        movimientos = (await db.execute(
            select(MovimientoAsiento).where(MovimientoAsiento.asiento_id == original.id)
        )).scalars().all()

        reverso = AsientoContable(
            fecha=original.fecha,
            descripcion=f"REVERSO — {motivo}",
            tipo_documento=original.tipo_documento,
            modulo_origen=original.modulo_origen,
            documento_ref=documento_ref,
            usuario_id=usuario_id,
            periodo_id=original.periodo_id,
        )
        db.add(reverso)
        await db.flush()
        for m in movimientos:
            db.add(MovimientoAsiento(
                asiento_id=reverso.id,
                cuenta_id=m.cuenta_id,
                tercero_id=m.tercero_id,
                centro_costo_id=m.centro_costo_id,
                debito=m.credito,   # espejo
                credito=m.debito,
            ))
        original.reversado = True
        reversos.append(reverso)

    await db.flush()
    return reversos


# ══════════════════════════════════════════════════════════
# Asientos por operación de negocio
# ══════════════════════════════════════════════════════════

async def asiento_venta_confirmada(db: AsyncSession, venta, usuario_id: int | None) -> AsientoContable:
    """DB Clientes + retenciones sufridas / CR Ingresos + IVA generado."""
    # Import local para no acoplar el módulo a nivel de import circular
    from app.modules.ventas.models import Cliente

    cliente = await db.get(Cliente, venta.cliente_id)
    tercero_id = await _get_or_create_tercero(
        db,
        cliente.nit_cc if cliente else None,
        cliente.razon_social if cliente else None,
        TipoTercero.CLIENTE,
    )
    return await registrar_asiento(
        db,
        fecha=venta.fecha,
        descripcion=f"Venta {venta.numero}",
        tipo_documento="Factura de venta",
        modulo_origen="ventas",
        documento_ref=venta.numero,
        usuario_id=usuario_id,
        centro_costo_id=venta.centro_costo_id,
        tercero_id=tercero_id,
        lineas=[
            ("130505", venta.total or CERO, CERO),
            ("135515", venta.retefuente or CERO, CERO),
            ("135517", venta.reteiva or CERO, CERO),
            ("135518", venta.reteica or CERO, CERO),
            ("413595", CERO, venta.base_gravable or CERO),
            ("240801", CERO, venta.iva_total or CERO),
        ],
    )


async def asiento_compra_confirmada(db: AsyncSession, compra, usuario_id: int | None) -> AsientoContable:
    """DB Inventario + IVA descontable / CR Proveedores + retenciones practicadas."""
    tercero_id = await _get_or_create_tercero(
        db, compra.proveedor_nit, compra.proveedor_razon_social, TipoTercero.PROVEEDOR
    )
    return await registrar_asiento(
        db,
        fecha=compra.fecha,
        descripcion=f"Compra {compra.numero} — {compra.proveedor_razon_social or ''}".strip(" —"),
        tipo_documento="Factura de compra",
        modulo_origen="compras",
        documento_ref=compra.numero,
        usuario_id=usuario_id,
        tercero_id=tercero_id,
        lineas=[
            ("143501", compra.base_gravable or CERO, CERO),
            ("240802", compra.iva_total or CERO, CERO),
            ("220501", CERO, compra.total or CERO),
            ("236540", CERO, compra.retefuente or CERO),
            ("236701", CERO, compra.reteiva or CERO),
            ("236801", CERO, compra.reteica or CERO),
        ],
    )


async def asiento_abono_cxc(db: AsyncSession, pago, cxc, usuario_id: int | None) -> AsientoContable:
    """Recibo de Caja: DB Caja / CR Clientes."""
    tercero_id = await _get_or_create_tercero(
        db, cxc.cliente_nit, cxc.nombre_cliente, TipoTercero.CLIENTE
    )
    return await registrar_asiento(
        db,
        fecha=pago.fecha.date() if hasattr(pago.fecha, "date") else pago.fecha,
        descripcion=f"Recibo de Caja {pago.numero_comprobante} — factura {cxc.numero_factura}",
        tipo_documento="Recibo de Caja",
        modulo_origen="cartera",
        documento_ref=pago.numero_comprobante,
        usuario_id=usuario_id,
        tercero_id=tercero_id,
        lineas=[
            ("110505", pago.valor, CERO),
            ("130505", CERO, pago.valor),
        ],
    )


async def asiento_abono_cxp(db: AsyncSession, pago, cxp, usuario_id: int | None) -> AsientoContable:
    """Comprobante de Egreso: DB Proveedores / CR Caja."""
    tercero_id = await _get_or_create_tercero(
        db, cxp.proveedor_nit, cxp.razon_social, TipoTercero.PROVEEDOR
    )
    return await registrar_asiento(
        db,
        fecha=pago.fecha.date() if hasattr(pago.fecha, "date") else pago.fecha,
        descripcion=f"Comprobante de Egreso {pago.numero_comprobante} — doc {cxp.numero_documento}",
        tipo_documento="Comprobante de Egreso",
        modulo_origen="cartera",
        documento_ref=pago.numero_comprobante,
        usuario_id=usuario_id,
        tercero_id=tercero_id,
        lineas=[
            ("220501", pago.valor, CERO),
            ("110505", CERO, pago.valor),
        ],
    )


async def asiento_devolucion_venta(
    db: AsyncSession, devolucion, venta, usuario_id: int | None
) -> AsientoContable:
    """Nota crédito: DB Devoluciones en ventas + IVA generado / CR Clientes.

    Limitación documentada: las retenciones de la factura original no se
    ajustan (la NC se emite por base + IVA); si el cliente ya practicó
    retenciones sobre lo devuelto, el ajuste es manual con el contador.
    """
    from app.modules.ventas.models import Cliente

    cliente = await db.get(Cliente, venta.cliente_id)
    tercero_id = await _get_or_create_tercero(
        db,
        cliente.nit_cc if cliente else None,
        cliente.razon_social if cliente else None,
        TipoTercero.CLIENTE,
    )
    return await registrar_asiento(
        db,
        fecha=devolucion.fecha,
        descripcion=f"Nota crédito {devolucion.numero} — devolución de venta {venta.numero}",
        tipo_documento="Nota crédito",
        modulo_origen="ventas",
        documento_ref=devolucion.numero,
        usuario_id=usuario_id,
        centro_costo_id=venta.centro_costo_id,
        tercero_id=tercero_id,
        lineas=[
            ("417501", devolucion.subtotal or CERO, CERO),
            ("240801", devolucion.iva_total or CERO, CERO),
            ("130505", CERO, devolucion.total or CERO),
        ],
    )


async def asiento_devolucion_compra(
    db: AsyncSession, devolucion, compra, usuario_id: int | None
) -> AsientoContable:
    """Devolución a proveedor: DB Proveedores / CR Inventario + IVA descontable."""
    tercero_id = await _get_or_create_tercero(
        db, compra.proveedor_nit, compra.proveedor_razon_social, TipoTercero.PROVEEDOR
    )
    return await registrar_asiento(
        db,
        fecha=devolucion.fecha,
        descripcion=f"Devolución {devolucion.numero} — compra {compra.numero}",
        tipo_documento="Devolución a proveedor",
        modulo_origen="compras",
        documento_ref=devolucion.numero,
        usuario_id=usuario_id,
        tercero_id=tercero_id,
        lineas=[
            ("220501", devolucion.total or CERO, CERO),
            ("143501", CERO, devolucion.subtotal or CERO),
            ("240802", CERO, devolucion.iva_total or CERO),
        ],
    )
