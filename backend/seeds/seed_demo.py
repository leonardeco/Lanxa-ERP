"""
Super Ozono Global — Seeder de datos DEMO (volumen para pruebas de UI).

Script CLI *independiente* que llena una **base de datos demo dedicada**
(`superozono_demo.db` por defecto) con ~50 clientes y ~200 ventas mixtas
(mayoría confirmadas), más los datos maestros mínimos (PUC, centros de costo,
períodos, parámetros, productos y clientes base). NO corre en el arranque de la
app y NUNCA toca la base de producción/desarrollo.

Uso (desde `backend/`):
    python -m seeds.seed_demo --clean --clientes 50 --ventas 200

Aislamiento: el script construye su PROPIO engine hacia la URL demo y se niega a
correr si esa URL coincide con `settings.DATABASE_URL` (producción). Limpieza:
`--clean` borra y recrea la BD demo (idempotente). Reproducible vía `--seed`.

Nota: los abonos parciales se aplican como ATAJO DEMO (se fija `abonos`/
`saldo_pendiente`/`estado` directo sobre la CxC, sin recibo de caja ni asiento de
abono) sólo para poblar el aging de Cartera. Los asientos de la venta sí son
correctos. Esto vive únicamente en la BD demo desechable.
"""

import os

# El validator de config.py exige sobrescribir SEED_ADMIN_PASSWORD cuando
# DEBUG=false. Se provee un valor propio ANTES de importar la app (mismo patrón
# que tests/conftest.py). La BD demo es desechable: no es una credencial real.
os.environ.setdefault("SEED_ADMIN_PASSWORD", "demo-seed-admin-pass")

import argparse  # noqa: E402
import asyncio  # noqa: E402
import random  # noqa: E402
from datetime import date, timedelta  # noqa: E402
from decimal import Decimal, ROUND_HALF_EVEN  # noqa: E402

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession, async_sessionmaker, create_async_engine,
)

from app.core.config import get_settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.modules.contabilidad.models import CuentaPorCobrar, EstadoDocumento  # noqa: E402
from app.modules.usuarios.models import Usuario  # noqa: E402
from app.modules.ventas.models import (  # noqa: E402
    Cliente, EstadoPago, EstadoVenta, Producto, VentaDetalle, VentaDocumento,
)
from app.modules.ventas.services import anular_venta, confirmar_venta  # noqa: E402
from seeds.seed import (  # noqa: E402
    seed_centros_costo, seed_clientes, seed_parametros_nomina,
    seed_parametros_tributarios, seed_periodos, seed_plan_cuentas,
    seed_productos, seed_usuarios,
)


DEFAULT_DEMO_URL = "sqlite+aiosqlite:///./superozono_demo.db"
_TWO = Decimal("0.01")
_MAX_VOLUMEN = 100_000


def _q(x: Decimal) -> Decimal:
    """Redondea a 2 decimales (half-even, como el resto del sistema)."""
    return Decimal(x).quantize(_TWO, rounding=ROUND_HALF_EVEN)


# ── Datos sintéticos para los clientes generados ─────────────────────────────
_CIUDADES = [
    ("Armenia", "Quindío"), ("Cali", "Valle del Cauca"), ("Bogotá", "Cundinamarca"),
    ("Medellín", "Antioquia"), ("Ibagué", "Tolima"), ("Pereira", "Risaralda"),
    ("Neiva", "Huila"), ("Bucaramanga", "Santander"), ("Manizales", "Caldas"),
    ("Villavicencio", "Meta"),
]
_RS_PREFIX = [
    "Agroinsumos", "Distribuidora", "Comercializadora", "Agrocampo", "Cultivos",
    "Agropecuaria", "Insumos", "Fumigaciones", "Agroservicios", "Cooperativa",
]
_RS_SUFFIX = [
    "del Campo", "Andina", "del Valle", "Tropical", "La Cosecha", "El Progreso",
    "Los Andes", "Verde", "del Eje", "Nacional",
]
_TIPO_REGIMEN = [
    ("Jurídica", "Responsable"), ("Natural", "No responsable"),
    ("Jurídica", "Gran contribuyente"),
]
_DIAS_CREDITO = [15, 30, 45, 60]


# ── Resolución de URL + guard de aislamiento ─────────────────────────────────

def resolve_demo_url(cli_url: str | None) -> str:
    """Precedencia: --db-url > SEED_DEMO_DATABASE_URL > DEFAULT_DEMO_URL."""
    if cli_url:
        return cli_url
    return os.environ.get("SEED_DEMO_DATABASE_URL") or DEFAULT_DEMO_URL


def assert_isolated(demo_url: str, prod_url: str) -> None:
    """Aborta si la URL demo apunta a producción o no es sqlite (salvo opt-in)."""
    if demo_url == prod_url:
        raise RuntimeError(
            f"La URL demo coincide con la de producción ({prod_url!r}). "
            "Abortando para no tocar datos reales."
        )
    if not demo_url.startswith("sqlite") and os.environ.get("SEED_DEMO_ALLOW_NONSQLITE") != "1":
        raise RuntimeError(
            f"La URL demo no es sqlite ({demo_url!r}). Si de verdad quieres una BD "
            "demo no-sqlite, exporta SEED_DEMO_ALLOW_NONSQLITE=1."
        )


def make_engine(demo_url: str):
    """Crea un engine + sessionmaker dedicados para la BD demo."""
    engine = create_async_engine(demo_url)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, sessionmaker


# ── Generadores ──────────────────────────────────────────────────────────────

async def boost_stock(session: AsyncSession, minimo: Decimal = Decimal("100000")) -> None:
    """Sube el stock de todos los productos y desactiva `controla_lote` para que
    ningún confirmar falle. Se fuerza el stock simple (no FEFO) porque el seeder no
    crea lotes: así el seeder es robusto aunque un dato base active lotes a futuro."""
    productos = (await session.execute(select(Producto))).scalars().all()
    for p in productos:
        if p.stock_actual is None or p.stock_actual < minimo:
            p.stock_actual = minimo
        p.controla_lote = False
    await session.flush()


async def generate_clientes(session: AsyncSession, n: int, rng: random.Random) -> list[int]:
    """Asegura al menos `n` clientes (los base cuentan). Devuelve todos los ids."""
    existing = (await session.execute(select(Cliente))).scalars().all()
    for idx in range(len(existing), n):
        ciudad, depto = rng.choice(_CIUDADES)
        tipo, regimen = rng.choice(_TIPO_REGIMEN)
        rs = f"{rng.choice(_RS_PREFIX)} {rng.choice(_RS_SUFFIX)} {idx:03d}"
        session.add(Cliente(
            nit_cc=f"9008{idx:05d}",
            dv=str(rng.randint(0, 9)),
            razon_social=rs.upper(),
            nombre_comercial=rs,
            tipo_persona=tipo,
            regimen_iva=regimen,
            direccion=f"Cra {rng.randint(1, 50)} #{rng.randint(1, 99)}-{rng.randint(1, 99)}",
            ciudad=ciudad,
            departamento=depto,
            celular=f"3{rng.randint(10, 29)}{rng.randint(1000000, 9999999)}",
            email=f"compras{idx}@demo-superozono.test",
            lista_precios=rng.choice(["General", "Mayorista", "Distribuidor"]),
            cupo_credito=Decimal(rng.choice([10, 20, 30, 50, 80, 100])) * Decimal("1000000"),
            dias_credito=rng.choice(_DIAS_CREDITO),
        ))
    await session.flush()
    return [c.id for c in (await session.execute(select(Cliente))).scalars().all()]


async def generate_ventas(
    session: AsyncSession, n: int, rng: random.Random, admin, cliente_ids: list[int],
) -> dict:
    """Crea `n` ventas mixtas: ~80% confirmadas, ~12% borrador, ~8% anuladas."""
    productos = (await session.execute(select(Producto))).scalars().all()
    counts = {"confirmadas": 0, "borrador": 0, "anuladas": 0}

    n_borrador = max(1, int(n * 0.12))
    n_anulada = max(1, int(n * 0.08))
    roles = ["anulada"] * n_anulada + ["borrador"] * n_borrador
    roles += ["confirmada"] * (n - len(roles))
    rng.shuffle(roles)

    today = date.today()
    for i in range(1, n + 1):
        role = roles[i - 1]
        cliente_id = rng.choice(cliente_ids)
        cliente = await session.get(Cliente, cliente_id)
        dias = cliente.dias_credito or 30
        fecha = today - timedelta(days=rng.randint(0, 365))

        venta = VentaDocumento(
            numero=f"SOG-V-{i:04d}",
            fecha=fecha,
            fecha_vencimiento=fecha + timedelta(days=dias),
            cliente_id=cliente_id,
            vendedor="Demo Seeder",
            estado=EstadoVenta.BORRADOR,
            estado_pago=EstadoPago.PENDIENTE,
        )
        session.add(venta)
        await session.flush()  # asigna venta.id antes de crear los detalles

        sub = desc = base = ivat = tot = Decimal("0")
        for p in rng.sample(productos, min(rng.randint(1, 5), len(productos))):
            cant = Decimal(rng.randint(1, 20))
            pu = p.precio_venta
            dpct = Decimal(rng.choice([0, 0, 0, 5, 10]))
            subl = _q(cant * pu)
            descl = _q(subl * dpct / Decimal("100"))
            basel = _q(subl - descl)
            ivp = p.tarifa_iva
            ivl = _q(basel * ivp / Decimal("100"))
            totl = _q(basel + ivl)
            session.add(VentaDetalle(
                venta_id=venta.id, producto_id=p.id, cantidad=cant,
                precio_unitario=pu, descuento_porcentaje=dpct,
                subtotal_linea=subl, iva_porcentaje=ivp, iva_valor=ivl, total_linea=totl,
            ))
            sub += subl; desc += descl; base += basel; ivat += ivl; tot += totl

        venta.subtotal = _q(sub)
        venta.descuento_total = _q(desc)
        venta.base_gravable = _q(base)
        venta.iva_total = _q(ivat)
        venta.total = _q(tot)
        await session.flush()  # persiste los detalles antes de confirmar (los re-lee)

        if role in ("confirmada", "anulada"):
            await confirmar_venta(session, venta, admin)
            if role == "anulada":
                await anular_venta(session, venta, admin)
                counts["anuladas"] += 1
            else:
                counts["confirmadas"] += 1
        else:
            counts["borrador"] += 1

    await session.commit()
    return counts


async def apply_demo_abonos(session: AsyncSession, rng: random.Random, fraccion: float = 0.35) -> int:
    """ATAJO DEMO: marca ~`fraccion` de las CxC PENDIENTE con un abono parcial/total
    (sin recibo de caja) para poblar el aging de Cartera. Devuelve cuántas tocó."""
    cxcs = (await session.execute(
        select(CuentaPorCobrar).where(CuentaPorCobrar.estado == EstadoDocumento.PENDIENTE)
    )).scalars().all()

    touched = 0
    for cxc in cxcs:
        if rng.random() > fraccion:
            continue
        valor = cxc.valor_factura or Decimal("0")
        if valor <= 0:
            continue

        if rng.random() < 0.4:
            abono, estado, epago = valor, EstadoDocumento.PAGADO, EstadoPago.PAGADO
        else:
            pct = Decimal(rng.choice([25, 50, 75]))
            abono = _q(valor * pct / Decimal("100"))
            estado, epago = EstadoDocumento.PARCIAL, EstadoPago.PARCIAL

        cxc.abonos = abono
        cxc.saldo_pendiente = _q(valor - abono)
        cxc.estado = estado
        cxc.notas = ((cxc.notas or "") + " [DEMO] abono simulado").strip()

        venta = (await session.execute(
            select(VentaDocumento).where(VentaDocumento.numero == cxc.numero_factura)
        )).scalar_one_or_none()
        if venta:
            venta.estado_pago = epago
        touched += 1

    await session.commit()
    return touched


# ── Orquestador ──────────────────────────────────────────────────────────────

async def run_demo_seed(
    *,
    demo_url: str = DEFAULT_DEMO_URL,
    clientes: int = 50,
    ventas: int = 200,
    clean: bool = False,
    seed: int = 42,
    sessionmaker=None,
    engine=None,
) -> dict:
    """Siembra la BD demo. Si `sessionmaker`/`engine` se inyectan (tests), se usan
    tal cual y se omite el guard de aislamiento; si no, se construyen desde
    `demo_url` tras validar el aislamiento."""
    settings = get_settings()
    own_engine = None
    if sessionmaker is None:
        assert_isolated(demo_url, settings.DATABASE_URL)
        own_engine, sessionmaker = make_engine(demo_url)
        engine = own_engine

    rng = random.Random(seed)

    async with engine.begin() as conn:
        if clean:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Rechazar re-ejecución sobre una BD demo ya poblada (idempotencia explícita)
    async with sessionmaker() as session:
        if (await session.scalar(select(VentaDocumento.id).limit(1))) and not clean:
            raise RuntimeError(
                "La BD demo ya tiene ventas. Usa --clean para regenerarla desde cero."
            )

    # Datos maestros base (idempotentes) — reutiliza los seeders existentes
    async with sessionmaker() as session:
        await seed_plan_cuentas(session)
        await seed_centros_costo(session)
        await seed_periodos(session)
        await seed_parametros_tributarios(session)
        await seed_parametros_nomina(session)
        await seed_usuarios(session)
        await seed_productos(session)
        await seed_clientes(session)

    async with sessionmaker() as session:
        await boost_stock(session)
        admin = (await session.execute(
            select(Usuario).where(Usuario.email == settings.SEED_ADMIN_EMAIL)
        )).scalar_one()
        cliente_ids = await generate_clientes(session, clientes, rng)
        await session.commit()
        counts = await generate_ventas(session, ventas, rng, admin, cliente_ids)
        con_abono = await apply_demo_abonos(session, rng)

    if own_engine is not None:
        await own_engine.dispose()

    return {**counts, "con_abono": con_abono, "clientes": len(cliente_ids), "ventas": ventas}


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="seed_demo",
        description="Seeder de datos DEMO para el ERP (base de datos dedicada, no producción).",
    )
    p.add_argument("--clientes", type=int, default=50, help="Número de clientes (def. 50)")
    p.add_argument("--ventas", type=int, default=200, help="Número de ventas (def. 200)")
    p.add_argument("--clean", action="store_true", help="Borra y recrea la BD demo antes de sembrar")
    p.add_argument("--seed", type=int, default=42, help="Semilla RNG para reproducibilidad (def. 42)")
    p.add_argument("--db-url", type=str, default=None, help="URL de la BD demo (override)")
    return p


def _validate_bounds(parser: argparse.ArgumentParser, args) -> None:
    if not (1 <= args.clientes <= _MAX_VOLUMEN):
        parser.error(f"--clientes debe estar entre 1 y {_MAX_VOLUMEN}")
    if not (1 <= args.ventas <= _MAX_VOLUMEN):
        parser.error(f"--ventas debe estar entre 1 y {_MAX_VOLUMEN}")


async def _amain(args) -> None:
    demo_url = resolve_demo_url(args.db_url)
    try:
        summary = await run_demo_seed(
            demo_url=demo_url,
            clientes=args.clientes,
            ventas=args.ventas,
            clean=args.clean,
            seed=args.seed,
        )
    except RuntimeError as exc:
        print(f"[SEED-DEMO] abortado: {exc}")
        raise SystemExit(1)

    print(
        f"[SEED-DEMO] listo -> BD={demo_url} clientes={summary['clientes']} "
        f"ventas={summary['ventas']} confirmadas={summary['confirmadas']} "
        f"borrador={summary['borrador']} anuladas={summary['anuladas']} "
        f"con_abono={summary['con_abono']}"
    )


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    _validate_bounds(parser, args)
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
