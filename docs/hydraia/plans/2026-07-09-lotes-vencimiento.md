# Plan — Lot + Expiry tracking

**Spec:** `docs/hydraia/specs/2026-07-09-lotes-vencimiento-design.md`
**Branch:** `feat/lotes-vencimiento`
Built in layers; each layer verified (tests/build) before the next.

## Layer 1 — Foundation (this step)

### Task 1.1 — `controla_lote` flag on Producto
Modify `backend/app/modules/ventas/models.py`: add after `stock_minimo`:
`controla_lote: Mapped[bool] = mapped_column(default=False)`.

### Task 1.2 — `Lote` model
Modify `backend/app/modules/inventario/models.py`: add `Lote` (table `lotes`):
`id, producto_id (FK productos.id, index), codigo_lote (String 60), fecha_vencimiento
(Date, nullable, index), cantidad_actual (Numeric 12,3), cantidad_inicial (Numeric
12,3), costo_unitario (Numeric 18,2, nullable), origen (String 40), fecha_ingreso
(DateTime default bogota_now), activo (bool default True)`. UniqueConstraint
`(producto_id, codigo_lote)`. `producto = relationship("Producto")`.
Add `lote_id: Mapped[int | None] = mapped_column(ForeignKey("lotes.id"), index=True)`
to `MovimientoInventario`.

### Task 1.3 — Alembic migration
Create `backend/alembic/versions/a1b2c3d4e5f6_lotes_vencimiento.py`,
`down_revision = "f1a2b3c4d5e6"`. `upgrade`: add column `productos.controla_lote`
(Boolean, server_default false, not null); create table `lotes`; add column
`movimientos_inventario.lote_id` (Integer, nullable, FK). Use `op.batch_alter_table`
for the SQLite-safe column adds. `downgrade`: reverse.

### Task 1.4 — Model tests
Create `backend/tests/test_lotes_modelo.py` (async, `db_session`): create a
lot-tracked Producto (`controla_lote=True`) + a `Lote`; assert persisted fields,
the unique constraint on `(producto_id, codigo_lote)`, and a `MovimientoInventario`
with `lote_id` set. Verify `venv/Scripts/python.exe -m pytest tests/test_lotes_modelo.py -q` green.

### Task 1.5 — Migration applies
Verify the migration runs on a throwaway SQLite DB: `alembic stamp f1a2b3c4d5e6`
then `alembic upgrade head` succeeds and `lotes` table + `controla_lote` +
`lote_id` exist; `alembic downgrade -1` reverts cleanly.

## Layer 2 — Lot service (next)
`inventario/lotes.py`: `entrada_lote(db, producto_id, cantidad, codigo_lote,
fecha_vencimiento, costo, origen, ...)` and `consumir_fefo(db, producto_id,
cantidad, ...)` (order by fecha_vencimiento nulls-last, skip/refuse expired,
decrement lots, one movement per lot). Invariant tests `stock_actual == Σ lotes`.

## Layer 3 — Wire-in
Route compras confirm/anular/devolución, ventas confirm/anular/devolución, ajuste,
importer through the lot service for lot-tracked products (unchanged path for
non-lot). Importer gains `codigo_lote`/`fecha_vencimiento` columns.

## Layer 4 — Alerts + frontend
Endpoints: existencias por lote, próximos a vencer (N días), vencidos. Inventario
dashboard widget + UI for lot entry and alerts.
