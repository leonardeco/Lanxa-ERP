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
- [ ] Phase 4 — Execution — Layer 1 (foundation)
- [ ] Phase 5 — Review
- [ ] Phase 6 — Verify & close (layer 1)

## Progreso por capas
- [ ] Capa 1 — modelo + migración + flag + tests
- [ ] Capa 2 — servicio de lotes (entrada + FEFO)
- [ ] Capa 3 — enganche compras/ventas/ajuste/importador
- [ ] Capa 4 — alertas + frontend
