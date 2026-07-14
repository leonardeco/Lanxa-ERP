# Design Spec — Demo data seeder (`seed_demo`)

- **Date:** 2026-07-14
- **Feature branch:** `feat/seeder-datos-demo`
- **Backlog item:** PENDIENTES.md 🔵 nice-to-have — "Seeder de datos demo (50 clientes, 200 ventas) para probar rendimiento de UI".

## Goal

Provide a standalone, idempotent CLI script that populates a **dedicated demo
database** with realistic volume (~50 clientes, ~200 ventas plus the minimum master
data those sales need) so the UI can be exercised under load. It must never touch the
production/dev database and must be trivially cleanable.

## Chosen approach + rejected alternatives

Four decisions were confirmed interactively with the user (Phase 2 brainstorming):

### 1. Data isolation — **Dedicated demo DB** (chosen)
A separate SQLite file `superozono_demo.db`, reached through a demo-specific
`DATABASE_URL` the script builds itself (its own `create_async_engine`), independent
of the global `app.core.database.engine` singleton.
- **Why:** "no tocar producción" and "limpiable" become structural guarantees, not
  discipline. `--clean` = drop+recreate the demo DB. Zero blast radius on real data.
- **Guard:** the script resolves the demo URL and **refuses to run** if it equals the
  configured production `DATABASE_URL`, or if the resolved URL is not the demo file.
- **Rejected — seed into dev DB with `[DEMO]` tags:** cleanup becomes a fragile
  selective-delete across 6+ tables (ventas, detalles, CxC, asientos, movimientos de
  inventario, clientes); one wrong filter corrupts real data. Not worth the risk.

### 2. Sales depth — **Realistic confirmed mix** (chosen)
Most ventas are **confirmed** through the real domain service `confirmar_venta()`, a
minority stay `Borrador`, a few are `Anulada`, and a subset carry a partial payment so
Cartera aging looks realistic.
- **Why:** confirming exercises the whole downstream surface (inventory/kardex, CxC,
  double-entry asientos, dashboards, P&L) — which is exactly the volume the UI perf
  test needs. Draft-only would leave Cartera/contabilidad/dashboards empty.
- **Rejected — Borrador only:** fast and simple but unrepresentative; the heaviest UI
  screens (Cartera, dashboards, contabilidad) would render against empty tables.

### 3. Invocation — **Standalone CLI** (chosen)
`python -m seeds.seed_demo --clientes 50 --ventas 200 --clean` (run from `backend/`).
- **Why:** never runs on production startup; carries its own params + `--clean`.
- **Rejected — hang off startup `SEED_DEMO`:** would run on every boot and offers no
  clean/param control.

### 4. Partial payments (abonos) — **documented demo shortcut**
There is no reusable abono service — the logic is embedded in
`contabilidad/router.py` (recibo-de-caja numbering + `asiento_abono_cxc` + CxC
update). Replicating it in the seeder would couple to router internals.
- **Chosen:** for a subset of confirmed ventas, set `CuentaPorCobrar.abonos`,
  `saldo_pendiente`, `estado` (PARCIAL/PAGADO) and the venta's `estado_pago` **directly**
  — no recibo de caja, no abono asiento. Clearly a demo-only shortcut, isolated in the
  demo DB, and labeled as such in the record `notas`.
- **Why acceptable:** the demo DB's purpose is UI volume, not ledger correctness; the
  sale asientos themselves stay correct. Faithful recibo-de-caja simulation is
  explicitly out of scope (can be added later via the real flow).

## Code-graph anchors (existing structure the design must respect)

- `backend/seeds/seed.py` — existing async, idempotent base seeder (`run_seeds`,
  `seed_plan_cuentas`, `seed_centros_costo`, `seed_periodos`, `seed_parametros_*`,
  `seed_usuarios`, `seed_productos`, `seed_clientes`). Constants `PLAN_CUENTAS_DATA`,
  `PRODUCTOS_DATA`, `CLIENTES_DATA` are reused as the base master data.
- `backend/app/core/database.py` — `Base`, and the module-level `engine` /
  `async_session` singletons built from `settings.DATABASE_URL` at import time. The
  demo script must **not** reuse these; it builds its own engine from the demo URL.
- `backend/app/core/config.py` — `Settings.DATABASE_URL` (required), `SEED_ADMIN_EMAIL`,
  `SEED_ADMIN_PASSWORD`, `DEBUG`. Backend dev URL: `sqlite+aiosqlite:///./superozono.db`.
- `backend/app/modules/ventas/models.py` — `VentaDocumento` (`numero` unique
  `SOG-V-####`, `fecha`, `fecha_vencimiento`, `cliente_id`, totals, `estado`
  EstadoVenta, `estado_pago` EstadoPago), `VentaDetalle` (`producto_id`, `cantidad`,
  `precio_unitario`, `descuento_porcentaje`, `subtotal_linea`, `iva_porcentaje`,
  `iva_valor`, `total_linea`), `Producto` (`stock_actual`, `precio_venta`,
  `tarifa_iva`, `controla_lote`), `Cliente` (`nit_cc` unique).
- `backend/app/modules/ventas/services.py` — `confirmar_venta(db, venta, usuario)`
  (validates stock → CONFIRMADA → inventory salida → CxC → `asiento_venta_confirmada`
  → `db.flush()`). Raises `VentaError` on insufficient stock. **The seeder must ensure
  stock ≥ demanded before confirming.**
- `backend/app/core/numbering.py` — `next_sequential_numero`; the demo DB starts empty
  after `--clean`, so numbers can be generated in-memory (`SOG-V-{i:04d}`) — no need
  for 200 MAX queries.
- `backend/app/modules/contabilidad/models.py` — `CuentaPorCobrar` (`numero_factura`,
  `abonos`, `saldo_pendiente`, `estado` EstadoDocumento PENDIENTE/PARCIAL/PAGADO),
  `EstadoDocumento`.
- `backend/tests/conftest.py` — test pattern: in-memory `sqlite+aiosqlite:///:memory:`,
  `Base.metadata.create_all`, seeds an admin + `ParametroTributario`. Seeder unit tests
  follow this pattern (own in-memory engine, no external DB).

## Global constraints (exact values)

- **Language:** user-facing narration in Spanish; code/commits/spec in English-portable.
- **Async everywhere** — the codebase is async SQLAlchemy 2.0; the seeder is `async`.
- **Idempotent:** re-running without `--clean` must not duplicate; `--clean` wipes the
  demo DB first (drop_all + create_all).
- **Demo DB only:** default demo URL `sqlite+aiosqlite:///./superozono_demo.db`
  (overridable via `--db-url` / `SEED_DEMO_DATABASE_URL`). Hard refusal if it resolves
  to the production `DATABASE_URL`.
- **Volume:** `--clientes` default 50, `--ventas` default 200 (both configurable).
- **Determinism:** seed the RNG (`random.Random(seed)`, default fixed) so runs are
  reproducible; expose `--seed`.
- **Stock safety:** before generating ventas, raise each demo product's `stock_actual`
  high enough (or cap line quantities) that no confirm hits `VentaError`.
- **Reuse, don't fork:** master data (PUC, centros de costo, periodos, parámetros,
  productos, clientes base) comes from the existing `seeds.seed` constants/functions.
- **No new runtime deps.** Uses stdlib `argparse`, `random`, `asyncio` + existing SA.
- **Version note:** the seeder is a dev/QA utility, not shipped in the prod startup path.

## Threat model + mitigations

Attack surface is small (a local dev/QA CLI, no network, no untrusted input), but:

- **T1 — Accidental production data loss.** `--clean` drops tables; if pointed at the
  real DB it would wipe production. **Mitigation:** the script resolves the demo URL and
  aborts with a clear error unless the target is the demo file and is *not* the
  configured production `DATABASE_URL`; `--clean` only ever runs against the demo
  engine the script itself built. (OWASP A05 misconfiguration.)
- **T2 — Weak admin password baked into demo.** The base seeder warns when the factory
  password is used. **Mitigation:** demo admin uses the same warning path; the demo DB
  is throwaway and never a production credential store. Documented as demo-only.
- **T3 — Resource exhaustion from silly `--ventas`.** A huge value could fill the disk.
  **Mitigation:** validate `--clientes`/`--ventas` are positive and within a sane cap
  (e.g. ≤ 100000), erroring otherwise.
- **T4 — Confidential data.** Demo clientes/NITs are synthetic and clearly fictitious;
  no real PII. (OWASP A02/A04 — none handled.)

## Adversarial pass (design self-review)

- *"Why not just call the existing `run_seeds()` with `SEED_DEMO=true`?"* — It runs on
  startup against the main DB and only creates 14 products / 6 clientes with **zero
  ventas**; it cannot produce 50/200 or isolate to a demo DB. Rejected above.
- *"Confirming 200 ventas may fail on stock."* — Real risk (`confirmar_venta` raises
  `VentaError`). Closed by the stock-safety constraint: bump `stock_actual` before
  confirming and/or cap per-line quantity to available stock.
- *"200 sequential MAX-numbering queries are O(n²)."* — Avoided: the demo DB is empty
  after `--clean`, so numbers are generated in-memory `SOG-V-0001..`.
- *"The abono shortcut makes the books inconsistent."* — Acknowledged and scoped: demo
  DB only, documented, sale asientos remain correct; faithful recibo flow out of scope.
- *"Idempotency vs confirmed side-effects."* — Re-running without `--clean` on a
  populated demo DB would double-confirm/duplicate numbers. Mitigation: the runner
  detects existing demo ventas and refuses without `--clean` (tells the user to pass
  `--clean`), so the only supported re-run path is clean-then-seed. Deterministic.
- *"Unit-testing a script that builds its own engine is hard."* — Mitigation: factor
  the generation logic into pure/async helper functions that accept a `session` (like
  the existing `seed_*`), so tests drive them against an in-memory engine per
  `conftest.py`; the `__main__`/CLI wiring stays thin.

## Success criteria

1. `python -m seeds.seed_demo --clean` (from `backend/`) creates `superozono_demo.db`
   with base master data + ~50 clientes + ~200 ventas, most confirmed.
2. Confirmed ventas produce matching CxC + asientos + inventory movements (no
   `VentaError`); a subset of CxC show PARCIAL/PAGADO for aging realism.
3. Re-running with `--clean` reproduces the same volume deterministically; without
   `--clean` on a populated demo DB it refuses instead of duplicating.
4. The script refuses to run against the production `DATABASE_URL`.
5. Unit tests cover: client/venta generators, stock-safety, isolation guard, and the
   idempotency/refusal path — all green in the existing pytest suite.
6. README / DOCUMENTACION note how to run it; PENDIENTES.md item moved to completed.
