# Implementation Plan — Demo data seeder (`seed_demo`)

- **Goal:** Standalone idempotent CLI that fills a dedicated demo SQLite DB with ~50
  clientes + ~200 ventas (mostly confirmed) + base master data, for UI perf testing.
- **Architecture:** A new async module `backend/seeds/seed_demo.py` builds its OWN
  async engine against a demo-only DB URL, reuses the base master-data seeders from
  `seeds/seed.py`, generates synthetic clientes and ventas, confirms most ventas
  through the real `ventas.services.confirmar_venta`, and applies a documented abono
  shortcut for aging realism. A thin `argparse` CLI drives it; generation logic is in
  session-taking helpers so pytest can drive them against an in-memory engine.
- **Tech stack:** Python 3.12 async, SQLAlchemy 2.0 (aiosqlite), stdlib argparse /
  random / asyncio. pytest + pytest-asyncio for tests.
- **Derives from spec:** `docs/hydraia/specs/2026-07-14-seeder-datos-demo-design.md`.

## Global Constraints (exact values)

- Demo DB default URL: `sqlite+aiosqlite:///./superozono_demo.db`; overridable via env
  `SEED_DEMO_DATABASE_URL` or `--db-url`. Run from `backend/`.
- Defaults: `--clientes 50`, `--ventas 200`, `--seed 42`. `--clean` wipes demo DB first.
- Async everywhere; determinism via `random.Random(seed)`.
- Isolation guard: abort if resolved demo URL == production `settings.DATABASE_URL`, or
  if the resolved URL does not start with `sqlite` and lacks an explicit opt-in.
- Stock safety: bump each product's `stock_actual` to a large value BEFORE confirming
  ventas so `confirmar_venta` never raises `VentaError`.
- Reuse base seeders from `seeds.seed` (do not duplicate PUC/productos/clientes base).
- No new runtime dependencies.
- Ventas numbering generated in-memory: `SOG-V-{i:04d}` starting at 1 (demo DB empty).
- Split mix over `--ventas`: ~80% CONFIRMADA, ~12% BORRADOR, ~8% ANULADA (anuladas are
  confirmed then annulled through `anular_venta`). Of the confirmed CxC, ~35% get a
  partial/paid abono via the documented shortcut.

## File Structure

| File | Responsibility |
|---|---|
| `backend/seeds/seed_demo.py` | **Create.** Demo engine builder + isolation guard, synthetic clientes/ventas generators, runner, argparse CLI. |
| `backend/tests/test_seed_demo.py` | **Create.** Unit tests for generators, stock-safety, isolation guard, idempotency/refusal. |
| `backend/seeds/__init__.py` | **Verify exists** (package import). Create empty if missing. |
| `README.md` | **Modify.** Add a "Seeder de datos demo" subsection under the existing seeding/dev docs. |
| `DOCUMENTACION.md` | **Modify.** Add a completed-item entry in §13. |
| `PENDIENTES.md` | **Modify.** Strike the 🔵 "Seeder de datos demo" line as done. |
| `.gitignore` | **Modify.** Ignore `superozono_demo.db` (+ `-shm`/`-wal`). |

---

## Task 1 — `seeds/seed_demo.py` (engine guard + generators + runner + CLI)

**Files:** `Create: backend/seeds/seed_demo.py`; verify/create `backend/seeds/__init__.py`.

**Environment:** run from `backend/` with the project venv active. No external services.

**Consumes (existing symbols — exact):**
- `from app.core.config import get_settings` → `settings.DATABASE_URL`,
  `settings.SEED_ADMIN_EMAIL`.
- `from app.core.database import Base`.
- `from seeds.seed import (seed_plan_cuentas, seed_centros_costo, seed_periodos,
  seed_parametros_tributarios, seed_parametros_nomina, seed_usuarios, seed_productos,
  seed_clientes)` — the base master-data seeders (each idempotent, take `session`).
- `from app.modules.ventas.models import (VentaDocumento, VentaDetalle, Producto,
  Cliente, EstadoVenta, EstadoPago)`.
- `from app.modules.usuarios.models import Usuario`.
- `from app.modules.contabilidad.models import CuentaPorCobrar, EstadoDocumento`.
- `from app.modules.ventas.services import confirmar_venta, anular_venta, VentaError`.
- `from sqlalchemy import select`, `from sqlalchemy.ext.asyncio import
  create_async_engine, async_sessionmaker, AsyncSession`.

**Produces (exact signatures later tasks/tests rely on):**
- `DEFAULT_DEMO_URL: str = "sqlite+aiosqlite:///./superozono_demo.db"`
- `def resolve_demo_url(cli_url: str | None) -> str` — precedence `cli_url` >
  `os.environ["SEED_DEMO_DATABASE_URL"]` > `DEFAULT_DEMO_URL`.
- `def assert_isolated(demo_url: str, prod_url: str) -> None` — raise
  `RuntimeError` if `demo_url == prod_url`, or if `demo_url` is not a sqlite URL and
  the env var `SEED_DEMO_ALLOW_NONSQLITE` is not `"1"`. Message names both URLs.
- `def make_engine(demo_url: str)` → returns `(engine, sessionmaker)`.
- `async def boost_stock(session: AsyncSession, minimo: Decimal = Decimal("100000")) -> None`
  — set every `Producto.stock_actual = max(current, minimo)` so confirms never fail.
- `async def generate_clientes(session: AsyncSession, n: int, rng: random.Random) -> list[int]`
  — ensure ≥ `n` clientes exist (base 6 already seeded count toward `n`); create the
  remainder as synthetic B2B clientes with unique `nit_cc` (format `9008{idx:05d}`),
  varied `razon_social`, `ciudad`, `tipo_persona`, `regimen_iva`, `dias_credito`
  (15/30/45/60), `cupo_credito`. Return all cliente ids.
- `async def generate_ventas(session, n, rng, admin, cliente_ids, split) -> dict` —
  create `n` `VentaDocumento` with 1–5 detalle lines each (random productos/qty),
  compute line + header totals exactly like the app (subtotal, descuento, base_gravable,
  iva_total, total; retenciones left 0 for demo simplicity), assign `numero`
  `SOG-V-{i:04d}`, `fecha` spread across the last 12 months, `fecha_vencimiento =
  fecha + dias_credito`. Then, per the split, confirm ~80% via `confirmar_venta`,
  leave ~12% BORRADOR, and confirm-then-`anular_venta` ~8%. Return counts dict
  `{"confirmadas": int, "borrador": int, "anuladas": int, "con_abono": int}`.
- `async def apply_demo_abonos(session, rng, fraccion: float = 0.35) -> int` — for a
  random `fraccion` of PENDIENTE CxC, set a partial or full `abonos`, recompute
  `saldo_pendiente = valor_factura - abonos`, set `estado` to PARCIAL or PAGADO, tag
  `notas` with `"[DEMO] abono simulado"`, and set the matching venta `estado_pago`.
  Return count touched.
- `async def run_demo_seed(*, demo_url, clientes, ventas, clean, seed, sessionmaker=None,
  engine=None) -> dict` — orchestrator: (if `clean`) drop_all+create_all else
  create_all; refuse (raise `RuntimeError`) if demo ventas already exist and not
  `clean`; run base seeders (plan_cuentas, centros_costo, periodos, parametros_*,
  usuarios, productos, clientes); `boost_stock`; `generate_clientes`; `generate_ventas`;
  `apply_demo_abonos`. Return a summary dict. When `sessionmaker`/`engine` are passed
  (tests), use them instead of building from `demo_url`.
- `def build_arg_parser() -> argparse.ArgumentParser` — flags `--clientes` (int, 50),
  `--ventas` (int, 200), `--clean` (store_true), `--seed` (int, 42), `--db-url` (str,
  None). Validate `clientes` in `1..100000` and `ventas` in `1..100000` (argparse
  `type` + explicit check raising `SystemExit` via `parser.error`).
- `async def _amain(args) -> None` and `def main() -> None` (sync wrapper calling
  `asyncio.run(_amain(...))`); `if __name__ == "__main__": main()`.

**Behavior details (exact):**
- **FIRST lines of the module, before importing any `app.*`:**
  `import os` then `os.environ.setdefault("SEED_ADMIN_PASSWORD", "demo-seed-admin-pass")`
  — the `config.py` validator raises when `DEBUG=false` and the admin password is the
  factory default; this mirrors the proven workaround in `tests/conftest.py`. Only then
  import `app.core.config`, `app.core.database`, the models, and the base seeders.
- **Flush ordering in `generate_ventas`:** `session.add(venta)` → `await
  session.flush()` (assigns `venta.id`) → build `VentaDetalle(venta_id=venta.id, ...)`
  and `session.add` each → `await session.flush()` (assigns detalle ids) → only THEN
  call `await confirmar_venta(session, venta, admin)` (it re-selects detalles by
  `venta.id`, so they must already be flushed). For anuladas: confirm, then
  `await anular_venta(session, venta, admin)`. Commit once per batch of ventas.
- **Isolation guard scope:** in `run_demo_seed`, run `assert_isolated` ONLY when the
  script builds the engine itself (i.e. when the injected `sessionmaker` is `None`);
  when tests inject a sessionmaker/engine, skip the guard.
- Totals per line: `subtotal_linea = cantidad * precio_unitario`;
  `descuento = subtotal_linea * descuento_porcentaje/100`;
  base = `subtotal_linea - descuento`; `iva_valor = base * iva_porcentaje/100`;
  `total_linea = base + iva_valor`. Quantize all money to 2 decimals
  (`Decimal.quantize(Decimal("0.01"))`). Header totals = sum of line parts.
- `iva_porcentaje` per line copied from the product's `tarifa_iva`.
- Isolation guard runs at the top of `run_demo_seed` (and again in `_amain`).
- Use `settings.SEED_ADMIN_EMAIL` to fetch the admin `Usuario` for `confirmar_venta`.
- Log a final one-line summary via `print()` (script context, not the app logger).

**Verification (run from `backend/`):**
1. `python -c "import ast; ast.parse(open('seeds/seed_demo.py').read()); print('OK')"` → `OK`.
2. `python -m seeds.seed_demo --clean --clientes 50 --ventas 200` → exits 0 and prints a
   summary line containing `confirmadas=`; a file `superozono_demo.db` now exists
   (`test -f superozono_demo.db && echo EXISTS` → `EXISTS`).
3. Re-run WITHOUT `--clean`: `python -m seeds.seed_demo` → exits non-zero with a message
   telling the user to pass `--clean` (refusal path).
4. `grep -c "SOG-V-" ...` not applicable (DB); instead verify via a tiny inline python:
   `python -c "import asyncio,seeds.seed_demo as s; ..."` count ventas == 200. (The
   pytest suite in Task 2 is the authoritative check; this step is a smoke test.)

**Commit:** `feat(seeds): standalone demo data seeder (50 clientes / 200 ventas)`.

---

## Task 2 — `tests/test_seed_demo.py` (unit tests, in-memory engine)

**Files:** `Create: backend/tests/test_seed_demo.py`.

**Environment:** run from `backend/`; `pytest` + `pytest-asyncio` already configured
(see `tests/conftest.py`). Tests build their OWN in-memory engine (do not reuse the
demo file) following the conftest pattern: `create_async_engine(
"sqlite+aiosqlite:///:memory:")`, `Base.metadata.create_all`, then a sessionmaker.
Imports: `from sqlalchemy import func, select`. Note: importing `seeds.seed_demo`
triggers its top-of-file `os.environ.setdefault("SEED_ADMIN_PASSWORD", ...)`, so no
extra env setup is needed in the test.

**Consumes:** the public functions produced by Task 1 (`resolve_demo_url`,
`assert_isolated`, `boost_stock`, `generate_clientes`, `generate_ventas`,
`apply_demo_abonos`, `run_demo_seed`, `build_arg_parser`).

**Test cases (each `@pytest.mark.asyncio` where async):**
- `test_resolve_demo_url_precedence` — cli > env > default.
- `test_assert_isolated_rejects_prod_url` — `assert_isolated(url, url)` raises
  `RuntimeError`; distinct sqlite urls pass.
- `test_run_demo_seed_volume` — call `run_demo_seed(demo_url="(memory)", clientes=50,
  ventas=200, clean=True, seed=42, sessionmaker=<test>, engine=<test>)`; assert
  `select(func.count()).select_from(Cliente)` ≥ 50 and `VentaDocumento` count == 200.
- `test_confirmed_have_cxc` — after seeding, count of CONFIRMADA ventas > 0 and each
  CONFIRMADA venta has a matching `CuentaPorCobrar` by `numero_factura`.
- `test_no_venta_error_on_confirm` — seeding a small run (`ventas=20`) raises no
  `VentaError` (stock-safety works).
- `test_abonos_populate_aging` — at least one CxC has `estado` in {PARCIAL, PAGADO}
  and `saldo_pendiente == valor_factura - abonos`.
- `test_rerun_without_clean_refuses` — seed once, then `run_demo_seed(..., clean=False)`
  on the populated sessionmaker raises `RuntimeError`.
- `test_arg_parser_defaults_and_bounds` — defaults are 50/200/42; `--ventas 0` and
  `--ventas 200001` cause `SystemExit`.

**Verification (from `backend/`):**
- `pytest tests/test_seed_demo.py -q` → all tests pass, `0 failed`.
- Full suite unaffected: `pytest -q` → the prior 277-API/component count still green
  (no regressions).

**Commit:** `test(seeds): cover demo seeder generators, isolation, idempotency`.

---

## Task 3 — Docs + gitignore

**Files:** `Modify: README.md`, `Modify: DOCUMENTACION.md`, `Modify: PENDIENTES.md`,
`Modify: .gitignore`.

**Steps:**
- `.gitignore`: add lines `superozono_demo.db`, `superozono_demo.db-shm`,
  `superozono_demo.db-wal` (anchor after the existing `*.db`/`superozono.db` entry;
  if `*.db` already covers it, add only a clarifying comment `# demo seeder DB`).
- `README.md`: under the existing seeding/desarrollo section, add a subsection
  "### Seeder de datos demo" documenting: purpose, the exact command
  `python -m seeds.seed_demo --clean --clientes 50 --ventas 200` (run from `backend/`),
  that it writes to `superozono_demo.db` (never production), `--clean` wipes it, and
  the `SEED_DEMO_DATABASE_URL` override.
- `DOCUMENTACION.md` §13: append a completed row/entry dated 2026-07-14: "Seeder de
  datos demo (CLI `seeds/seed_demo.py`): 50 clientes + 200 ventas mixtas en BD demo
  dedicada, idempotente con `--clean`, guard anti-producción; N tests."
- `PENDIENTES.md`: in the 🔵 Nice-to-have list, replace
  `- Seeder de datos demo (50 clientes, 200 ventas) para probar rendimiento de UI`
  with the struck+checked form
  `- ~~Seeder de datos demo (50 clientes, 200 ventas)~~ ✅ **Hecho 2026-07-14** (CLI \`seeds/seed_demo.py\`, BD demo dedicada; ver DOCUMENTACION.md §13)`.

**Verification:**
- `grep -c "seed_demo" README.md` → ≥ 1.
- `grep -c "Hecho 2026-07-14" PENDIENTES.md` → ≥ 1.
- `grep -c "superozono_demo.db" .gitignore` → ≥ 1.

**Commit:** `docs(seeds): document demo seeder; mark PENDIENTES item done`.
