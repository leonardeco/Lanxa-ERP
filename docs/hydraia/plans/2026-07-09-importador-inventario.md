# Plan — Inventory importer

**Spec:** `docs/hydraia/specs/2026-07-09-importador-inventario-design.md`
**Branch:** `feat/importador-inventario`

## File structure
| File | Action | Responsibility |
|---|---|---|
| `backend/requirements.txt` | modify | add `openpyxl` |
| `backend/app/modules/inventario/importador.py` | create | `EXPECTED_HEADERS`, `generar_plantilla()`, `validar()`, `importar()` |
| `backend/app/modules/inventario/schemas.py` | modify | `ErrorFilaImport`, `PreviewImport`, `ResumenImport` |
| `backend/app/modules/inventario/router.py` | modify | `GET /plantilla`, `POST /importar` |
| `backend/tests/test_importador_inventario.py` | create | validation + import + atomicity |
| `frontend/src/services/inventarioApi.ts` | modify | `descargarPlantilla()`, `importar(file, commit)` |
| `frontend/src/views/InventarioView.tsx` | modify | "Importar" tab (download / validate / confirm) |
| `PENDIENTES.md`, `DOCUMENTACION.md`, `BITACORA.md` | modify | close-out |

Working dir for commands: `backend/` (venv) and `frontend/`.

## Task 1 — openpyxl dependency
Add `openpyxl==3.1.5` to `backend/requirements.txt` (near other libs). Install into venv.
Verify: `venv/Scripts/python.exe -c "import openpyxl"` exits 0.

## Task 2 — importador.py core (TDD)
`validar(contenido: bytes, db) -> ResultadoValidacion(filas_ok, errores, total_filas)`.
Rules per spec (required fields, enum membership, numeric ≥0, iva∈{19,5,0}, sku
unique-in-file + not-in-DB, centro_costo_codigo resolves). Header mapping by name;
missing required header → single error. Blank rows skipped.
`importar(db, filas_ok, usuario)`: create `Producto(**data, stock_actual=0)`, flush,
`registrar_movimiento(ENTRADA, AJUSTE_MANUAL, cantidad=stock_inicial, motivo,
costo_unitario=costo, usuario_id)` when stock>0, `registrar_auditoria("Crear")`,
single `commit`. Returns `{"creados": n}`.
`generar_plantilla() -> bytes`: workbook with Inventario (headers + dropdowns for
categoria/unidad/iva, blank) + Instrucciones sheet.
Tests `test_importador_inventario.py` (async, `db_session` fixture, build xlsx bytes
in-memory with openpyxl): valid rows import; invalid enum, missing required, dup sku
in file, existing sku → errores; commit creates Producto + MovimientoInventario;
error path writes nothing.

## Task 3 — schemas + endpoints
`schemas.py`: `ErrorFilaImport(fila:int, columna:str, mensaje:str)`,
`PreviewImport(total_filas:int, validas:int, errores:list[ErrorFilaImport])`,
`ResumenImport(importados:int)`.
`router.py`: `GET /plantilla` → `Response(generar_plantilla(), xlsx media type,
Content-Disposition attachment)`, Admin/Administradora. `POST /importar`
(`archivo: UploadFile`, `commit: bool = Query(False)`): read bytes, `validar`; on
parse failure → 400; if `not commit` → return `PreviewImport`; if errores → 422 with
errores; else `importar` → `ResumenImport`. Both Admin/Administradora.
Verify: pytest green; `GET /plantilla` returns 200 xlsx in a test.

## Task 4 — frontend
`inventarioApi.ts`: `descargarPlantilla()` (GET blob), `importar(file, commit)`
(FormData POST, `params:{commit}`). `InventarioView.tsx`: add "Importar" tab —
Descargar plantilla button, file input, Validar (commit=false → preview table),
Confirmar importación (commit=true) enabled only when 0 errores, Toast + refresh.
Verify: `npm run lint`, `npx tsc --noEmit`, `npm run build` green.

## Task 5 — docs
PENDIENTES: note #2 importer done (real data still pending contadora). DOCUMENTACION
item 50. BITACORA session. Verify greps.
