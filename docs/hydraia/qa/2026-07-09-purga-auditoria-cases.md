# QA Cases — #28 Audit log purge/archival

**Date:** 2026-07-09
**Spec:** `docs/hydraia/specs/2026-07-09-purga-auditoria-design.md`
**Plan:** `docs/hydraia/plans/2026-07-09-purga-auditoria.md`
**Under test:** `app/modules/auditoria/purge.py::purgar_auditoria` + `scripts/purge_auditoria.py`

> Note: the `qa-functional` sub-agent could not read the repo from this session
> (sandbox root = System32), so these cases were authored directly by the Opus
> planning session from the spec. `Test ref`s point at the tests that shipped.

## Acceptance criteria

- **AC1** — Records with `fecha < cutoff` are deleted.
- **AC2** — Records newer than the cutoff are kept.
- **AC3** — Before deleting, the old records are exported to a Fernet-encrypted
  file that decrypts back to exactly those records (with `cambios` as a
  structured object).
- **AC4** — When there is nothing to purge, no file is created and the run exits 0.
- **AC5** — When there are records to purge but no encryption key, the run aborts
  and deletes nothing.
- **AC6** — The purge action is itself recorded in the audit log.

## Cases (Given / When / Then)

### TC-1.1 — Old records purged, recent kept (AC1, AC2, AC6)
- **Given** audit records at 2000 and 1900 days old and one at 10 days old, and a
  valid encryption key.
- **When** `purgar_auditoria` runs with cutoff = now − 1825 days.
- **Then** it returns `registros == 2`; only the recent `Crear` record remains
  plus a new `Purgar/Auditoria` record whose description contains "2 registros".

### TC-1.2 — Encrypted archive round-trips (AC3)
- **Given** one record 2000 days old and a valid key.
- **When** the purge runs.
- **Then** the produced `.json.enc` file, decrypted with the same key, is a JSON
  array of exactly 1 record; `usuario_email` matches and `cambios.precio.despues`
  is the structured value `"2"` (not a JSON string).

### TC-1.3 — Nothing to purge (AC4)
- **Given** only a recent record (10 days old) and no key.
- **When** the purge runs with cutoff = now − 1825 days.
- **Then** it returns `registros == 0`, `archivo is None`, and the archive
  directory has no files.

### TC-1.4 — Missing key aborts without deleting (AC5)
- **Given** one record 2000 days old and an empty encryption key.
- **When** the purge runs.
- **Then** it raises `ValueError` and the audit table still contains the record
  (nothing deleted, no file written).

### TC-1.5 — CLI wrapper end-to-end smoke (AC4 via script)
- **Given** an empty audit table and default retention.
- **When** `scripts/purge_auditoria.py` runs.
- **Then** it prints `Nada que purgar (...)`, exits 0, and creates no archive
  folder. (Verified manually against a temp SQLite DB during the run.)

## Traceability matrix

| AC | Cases | Test ref |
|---|---|---|
| AC1 | TC-1.1 | `backend/tests/test_purge_auditoria.py::test_purga_borra_viejos_conserva_recientes` |
| AC2 | TC-1.1 | `backend/tests/test_purge_auditoria.py::test_purga_borra_viejos_conserva_recientes` |
| AC3 | TC-1.2 | `backend/tests/test_purge_auditoria.py::test_archivo_cifrado_descifra_a_los_registros` |
| AC4 | TC-1.3, TC-1.5 | `backend/tests/test_purge_auditoria.py::test_sin_registros_no_crea_archivo` · CLI smoke — manual (run log) |
| AC5 | TC-1.4 | `backend/tests/test_purge_auditoria.py::test_falta_clave_aborta_sin_borrar` |
| AC6 | TC-1.1 | `backend/tests/test_purge_auditoria.py::test_purga_borra_viejos_conserva_recientes` |

## GAPS / open questions

- **Retention default (resolved):** 5 years (1825 days), configurable via `.env`.
  Chosen over 2 years to cover the DIAN fiscal firmeza window. Business may adjust
  per legal advice.
- **Archive rotation:** the encrypted purge archives themselves accumulate in
  `{BACKUP_DIR}/auditoria/`. Not in scope for #28; if volume grows, a future item
  can prune archives older than N years (they are the last-resort trail, so keep
  conservatively).
- **Multi-DB:** logic is ORM-based so it works on both SQLite (prod `start.bat`)
  and PostgreSQL (Docker); only SQLite path was smoke-run this session.
