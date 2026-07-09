# Design Spec — Lot + Expiry tracking (traceability)

**Date:** 2026-07-09
**Context:** Super Ozono makes certified-organic ozonated products. Lot + expiry
traceability is the top functional gap (recalls, ICA registration, organic
certification, FEFO to minimize waste).

## Goal

Track inventory by **lot** with an **expiration date**, opt-in per product, with
**FEFO** depletion, expiry **alerts**, and lot **traceability** in the kardex —
without breaking existing stock/reports.

## Decisions (confirmed with the user)

- **Opt-in per product** — `Producto.controla_lote` flag. Durable goods (ozone
  generators) stay single-stock; perishable oils/organics enable lots.
- **FEFO** — sales/outflows auto-deplete the earliest-expiring lot first; expired
  lots are not sold.
- **MVP** — lots via purchases / importer / manual entry, FEFO on sales, expiry
  alerts, lot traceability. Production-generated lots are OUT (no production module
  yet); multi-warehouse lots OUT (#21b).

## Data model

- `Producto.controla_lote: bool = False` (new column).
- New `Lote` (table `lotes`): `id, producto_id (FK), codigo_lote, fecha_vencimiento
  (nullable), cantidad_actual, cantidad_inicial, costo_unitario, origen,
  fecha_ingreso, activo`. Unique `(producto_id, codigo_lote)`.
- `MovimientoInventario.lote_id: int | None` (FK to `lotes`) — lot traceability in
  the kardex.
- `stock_actual` stays as the **aggregate** (= Σ active lots for lot-tracked
  products) so the dashboard, reports and stock validation keep working.

**Invariant:** for a lot-tracked product, `stock_actual == Σ lotes.cantidad_actual`.
A single service layer updates both the lot and the aggregate in one transaction.

## Lot lifecycle / integration points

- **Entradas** (compra confirm, importer, manual adjustment): for lot-tracked
  products, the entry carries `codigo_lote + fecha_vencimiento`. The service
  creates/increments the `Lote`, raises `stock_actual`, and records the movement
  with `lote_id`.
- **Salidas** (venta confirm, adjustment): `consumir_fefo()` allocates the quantity
  across lots ordered by `fecha_vencimiento` (nulls last), decrements each lot,
  refuses expired lots, and records one movement per lot touched.
- **Reversals** (anular/devolución): restore quantity to the referenced lot.
- **Alerts/reports:** existencias por lote, próximos a vencer (N days), vencidos;
  Inventario dashboard widget.

The 7 stock-mutation sites (compras confirm/anular/devolución, ventas
confirm/anular/devolución, ajuste, importer) route through the lot-aware layer.

## Global constraints

- `codigo_lote` unique per product; same code on a new entry increments the lot.
- Non-lot products behave exactly as today (no regression).
- Migration must run on SQLite (batch mode) and PostgreSQL.
- Numeric(12,3) for lot quantities (fractional, like stock).

## Threat model

Internal, Admin/Administradora surface. Main risk: aggregate/lot drift → mitigated
by a single transactional layer + tests asserting `stock_actual == Σ lotes`. FEFO
refusing expired lots prevents shipping expired product (safety/compliance).

## Layered build (verified at each layer)

1. **Foundation:** `controla_lote` flag, `Lote` model, `lote_id` on kardex, Alembic
   migration, model tests. ← this layer.
2. **Lot service:** `entrada_lote()` + `consumir_fefo()` + invariant tests.
3. **Wire-in:** compras/ventas/ajuste/importer route through the service.
4. **Alerts + frontend:** existencias por lote, expiry alerts, dashboard widget, UI.

Out of scope (documented): production lots, multi-warehouse lots, lot-level layered
costing.
