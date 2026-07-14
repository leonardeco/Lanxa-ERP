"""Unit tests for the standalone demo data seeder (`seeds.seed_demo`).

Each test drives the generators against its OWN in-memory SQLite engine (StaticPool
so the multiple sessions inside `run_demo_seed` share one DB), independent of the
production/demo file. Importing `seeds.seed_demo` sets `SEED_ADMIN_PASSWORD` via
`os.environ.setdefault`, so no extra env setup is needed here.
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import seeds.seed_demo as sd
from app.modules.contabilidad.models import CuentaPorCobrar, EstadoDocumento
from app.modules.ventas.models import Cliente, EstadoVenta, VentaDocumento


@pytest_asyncio.fixture
async def demo_env():
    """A private in-memory engine + sessionmaker shared across sessions (StaticPool)."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, sm
    await engine.dispose()


# ── Pure/CLI helpers ─────────────────────────────────────────────────────────

def test_resolve_demo_url_precedence():
    os.environ.pop("SEED_DEMO_DATABASE_URL", None)
    assert sd.resolve_demo_url("cli://x") == "cli://x"
    os.environ["SEED_DEMO_DATABASE_URL"] = "env://y"
    try:
        assert sd.resolve_demo_url(None) == "env://y"
    finally:
        os.environ.pop("SEED_DEMO_DATABASE_URL", None)
    assert sd.resolve_demo_url(None) == sd.DEFAULT_DEMO_URL


def test_assert_isolated_rejects_prod_url():
    with pytest.raises(RuntimeError):
        sd.assert_isolated("sqlite+aiosqlite:///./x.db", "sqlite+aiosqlite:///./x.db")
    # distinct sqlite urls must pass
    sd.assert_isolated("sqlite+aiosqlite:///./demo.db", "sqlite+aiosqlite:///./prod.db")


def test_arg_parser_defaults_and_bounds():
    p = sd.build_arg_parser()
    a = p.parse_args([])
    assert (a.clientes, a.ventas, a.seed) == (50, 200, 42)
    for bad in ("0", "100001"):
        with pytest.raises(SystemExit):
            sd._validate_bounds(p, p.parse_args(["--ventas", bad]))


# ── Seeding behaviour ────────────────────────────────────────────────────────

async def test_run_demo_seed_volume(demo_env):
    engine, sm = demo_env
    summary = await sd.run_demo_seed(
        clientes=50, ventas=200, clean=True, seed=42, sessionmaker=sm, engine=engine,
    )
    async with sm() as s:
        nclientes = await s.scalar(select(func.count()).select_from(Cliente))
        nventas = await s.scalar(select(func.count()).select_from(VentaDocumento))
    assert nclientes >= 50
    assert nventas == 200
    assert summary["confirmadas"] > 0


async def test_no_venta_error_on_confirm(demo_env):
    engine, sm = demo_env
    # boost_stock must guarantee no VentaError is raised while confirming.
    await sd.run_demo_seed(
        clientes=10, ventas=20, clean=True, seed=1, sessionmaker=sm, engine=engine,
    )


async def test_confirmed_have_cxc(demo_env):
    engine, sm = demo_env
    await sd.run_demo_seed(
        clientes=20, ventas=40, clean=True, seed=7, sessionmaker=sm, engine=engine,
    )
    async with sm() as s:
        confirmadas = (await s.execute(
            select(VentaDocumento).where(VentaDocumento.estado == EstadoVenta.CONFIRMADA)
        )).scalars().all()
        assert confirmadas
        for v in confirmadas:
            cxc = await s.scalar(
                select(CuentaPorCobrar).where(CuentaPorCobrar.numero_factura == v.numero)
            )
            assert cxc is not None


async def test_abonos_populate_aging(demo_env):
    engine, sm = demo_env
    await sd.run_demo_seed(
        clientes=20, ventas=60, clean=True, seed=3, sessionmaker=sm, engine=engine,
    )
    async with sm() as s:
        rows = (await s.execute(
            select(CuentaPorCobrar).where(
                CuentaPorCobrar.estado.in_([EstadoDocumento.PARCIAL, EstadoDocumento.PAGADO])
            )
        )).scalars().all()
    assert rows
    for cxc in rows:
        assert cxc.saldo_pendiente == (cxc.valor_factura - cxc.abonos)


async def test_rerun_without_clean_refuses(demo_env):
    engine, sm = demo_env
    await sd.run_demo_seed(
        clientes=10, ventas=15, clean=True, seed=5, sessionmaker=sm, engine=engine,
    )
    with pytest.raises(RuntimeError):
        await sd.run_demo_seed(
            clientes=10, ventas=15, clean=False, seed=5, sessionmaker=sm, engine=engine,
        )
