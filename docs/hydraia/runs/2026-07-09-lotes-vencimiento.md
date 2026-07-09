# Run log — Lot + Expiry tracking

**Request:** Construir el módulo de lote + vencimiento (trazabilidad) por capas.
**Branch:** `feat/lotes-vencimiento`
**Spec:** `docs/hydraia/specs/2026-07-09-lotes-vencimiento-design.md`
**Plan:** `docs/hydraia/plans/2026-07-09-lotes-vencimiento.md`
**Decisiones:** opt-in por producto · FEFO automático · MVP (sin producción).

## Phase checklist
- [x] Phase 0 — Context
- [x] Phase 1 — Think
- [x] Phase 2 — Design + spec (approved)
- [x] Phase 3 — Plan (layered) + self-review (frozen)
- [x] Phase 4 — Execution — Layer 1 (foundation)
- [x] Phase 5 — Review (Opus; invariante y batch-migration cubiertas)
- [x] Phase 6 — Verify & close (layer 1)

## Progreso por capas
- [x] Capa 1 — modelo + migración + flag + tests (3 tests, mypy/flake8 limpios, migración up/down verificada)
- [ ] Capa 2 — servicio de lotes (entrada + FEFO)
- [ ] Capa 3 — enganche compras/ventas/ajuste/importador
- [ ] Capa 4 — alertas + frontend

## Capa 1 — resultado
- `Producto.controla_lote` (default false), modelo `Lote` (tabla `lotes`, único por producto+código), `MovimientoInventario.lote_id`.
- Migración `a1b2c3d4e5f6` (down_revision f1a2b3c4d5e6), batch-safe SQLite/PG. upgrade head + downgrade -1 verificados en DB temporal.
- Tests `test_lotes_modelo.py` (3). Sin migrar stock existente (arranca controla_lote=false).
