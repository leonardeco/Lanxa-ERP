# Design Spec — Inventory importer (initial load)

**Date:** 2026-07-09
**Issue:** #2 (partial) — carga de datos maestros: inventario inicial vía plantilla.

## Goal

Let the team load the real initial inventory from the blank Excel template the
auxiliar fills: upload → validate every row → preview errors → on confirm, create
the products with their initial stock (recorded in the kardex), atomically.

## Chosen approach

- **Backend module** `app/modules/inventario/importador.py` holds the single source
  of truth for the columns (`EXPECTED_HEADERS`), the template generator
  (`generar_plantilla() -> bytes`), the validator (`validar(bytes, db)`), and the
  importer (`importar(db, filas, usuario)`). Pure functions → unit-testable.
- **Endpoint** `POST /api/v1/inventario/importar` (Admin/Administradora):
  `commit=false` (default) returns a **preview** (row count + per-row errors,
  writes nothing); `commit=true` imports **only if zero errors** (else HTTP 422),
  in one transaction. `GET /api/v1/inventario/plantilla` downloads the blank xlsx
  (generated in code, so it can never drift from `EXPECTED_HEADERS`).
- **Initial stock through the kardex:** each product is created with `stock_actual=0`
  then a `registrar_movimiento(ENTRADA, origen=AJUSTE_MANUAL, motivo="Inventario
  inicial (importación)")` sets the stock — the kardex shows a truthful entry. Each
  creation is audited. All-or-nothing (single commit).
- **Frontend:** new "Importar" tab in `InventarioView.tsx` — download template,
  pick .xlsx, Validate (shows N OK / error table), then Confirm import.
- **New dependency:** `openpyxl` (backend reads/writes .xlsx). `python-multipart`
  already present for `UploadFile`.

## Rejected alternatives

- Set `stock_actual` directly (like `create_producto`) — simpler but leaves no
  kardex trace of how the initial stock arrived; rejected for auditability.
- Partial import (import valid rows, skip invalid) — rejected: for an initial load,
  atomic all-or-nothing with a clear error report is safer and less confusing.
- Add an `OrigenMovimiento.INVENTARIO_INICIAL` enum — avoided to skip a model change
  + migration; reuse `AJUSTE_MANUAL` + a clear `motivo`.

## Code-graph anchors

- `Producto`, `CategoriaProducto`, `UnidadMedida` in `app/modules/ventas/models.py`.
- `CentroCosto` (field `codigo`) in `app/modules/contabilidad/models.py`.
- `registrar_movimiento` in `app/modules/inventario/service.py`
  (tipo `TipoMovimientoInventario.ENTRADA`, origen `OrigenMovimiento.AJUSTE_MANUAL`).
- `registrar_auditoria` in `app/modules/auditoria/service.py`.
- Router `app/modules/inventario/router.py` (prefix `/api/v1/inventario`, deps
  `AdminOrAdministradoraDep`, `get_db`).
- Frontend `frontend/src/views/InventarioView.tsx` (tabs + `Toast`),
  `frontend/src/services/inventarioApi.ts` (axios `api`).

## Global constraints

- Required columns: `sku, nombre, categoria, marca, unidad_medida, precio_venta,
  tarifa_iva, stock_actual`. Optional: `contenido_neto, precio_costo, stock_minimo,
  registro_ica, centro_costo_codigo, descripcion, notas`.
- `categoria ∈ {Biocida,Fertilizante,Coadyuvante,Desinfectante,Otro}`;
  `unidad_medida ∈ {Litro,Galón,Kilo,Unidad,Caja,Caneca}`; `tarifa_iva ∈ {19,5,0}`;
  `precio_venta, stock_actual, precio_costo ≥ 0`.
- SKU: required, unique within the file, and **must not already exist** in DB → else
  a row error (no overwrite).
- `centro_costo_codigo`, if present, must match an existing `CentroCosto.codigo`.
- Column order is header-name based (order-independent); a missing required header
  fails the whole file.

## Threat model

Untrusted file upload + bulk DB writes. Mitigations: Admin/Administradora only;
parse in-memory with openpyxl (no macro execution); every row validated before any
write; import is atomic (rollback on error); each product creation audited; no
secrets/PII involved. Out of scope: accounting opening entry (blocked by contadora
decision #3, método de costeo) — documented as follow-up.

## Scope

Backend: openpyxl dep, `importador.py`, 2 endpoints, response schemas, tests.
Frontend: api methods + "Importar" tab. Docs: PENDIENTES/DOCUMENTACION/BITACORA.
