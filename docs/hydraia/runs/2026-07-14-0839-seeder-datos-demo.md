# Hydraia run — Demo data seeder

- **Started:** 2026-07-14 08:39
- **Request:** Implementar un seeder de datos demo (~50 clientes, ~200 ventas + maestros
  mínimos) para probar rendimiento de UI. Idempotente/limpiable, claramente demo, sin
  tocar producción. Backlog 🔵 nice-to-have de PENDIENTES.md.
- **Spec:** `docs/hydraia/specs/2026-07-14-seeder-datos-demo-design.md`
- **Plan:** `docs/hydraia/plans/2026-07-14-seeder-datos-demo.md`
- **Branch:** `feat/seeder-datos-demo`
- **Language:** Español · **Model:** Opus 4.8 (main)

## Decisions (interactive)
- Dedicated demo DB (`superozono_demo.db`), own engine, prod-URL guard.
- Realistic confirmed mix (~80% confirmed / ~12% draft / ~8% annulled; ~35% CxC abono).
- Standalone CLI `python -m seeds.seed_demo`.
- Abonos as documented demo shortcut (no recibo de caja).

## Efficiency note
Phase 4 executed by the main Opus session (contained 2-file backend utility with full
context) rather than fanning out cold executor subagents; Phase 5 review dispatched to
subagents where independent eyes add value. Disclosed to user.

## Phase checklist
- [x] Phase 0 — Context (existing seed.py, models, services, numbering, conftest)
- [x] Phase 1 — Think
- [x] Phase 2 — Design + spec + threat model + adversarial pass
- [x] Phase 3 — Plan + 2-pass self-review + QA cases + gate armed
- [x] Phase 4 — Execution
- [x] Phase 5 — Review (self-run by main Opus; subagents sandbox-blocked from repo path)
- [x] Phase 6 — Verify (full pytest: 285 passed; seeder 8 + e2e smoke re-verified)
