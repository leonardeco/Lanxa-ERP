# Design Spec — #28 Audit log purge/archival

**Date:** 2026-07-09
**Issue:** #28 (PENDIENTES.md — "Purga/archivado del log de auditoría")
**Author:** Hydraia pipeline (Opus 4.8 planning)

## Goal

The `auditoria` table grows without bound. Provide a safe, traceable way to
**archive and then purge** audit records older than a configurable retention
period: export the old records to an encrypted file first, verify the export,
then delete them — never losing the trail, and recording the purge itself.

## Chosen approach + rejected alternatives

**Chosen — standalone maintenance script backed by a reusable async module
function.** The core logic lives in `app/modules/auditoria/purge.py` as
`purgar_auditoria(...)`, so it is unit-testable with the existing async DB
fixtures. A thin CLI wrapper `scripts/purge_auditoria.py` mirrors the existing
`scripts/backup_db.py` (run manually or from Windows Task Scheduler). No new
API or UI surface.

- **Rejected — admin endpoint + UI button.** Adds an authenticated *deletion*
  path over the audit trail (larger risk surface on the very data meant to be
  tamper-evident) plus frontend work. Discoverability does not justify the added
  surface for a once-in-a-while maintenance action.
- **Rejected — raw `sqlite3` script (like backup_db.py internals).** Simpler but
  hardcodes the schema and is harder to unit-test; reusing the ORM model keeps
  `cambios` serialization consistent and lets the logic run under the async test
  fixtures.
- **Rejected — automatic background job inside the app.** Adds a scheduler
  dependency and runs destructive deletes unattended inside the request process;
  a script under the admin's control (same trust level as backups) is safer and
  matches the project's existing operational model.

## Code-graph anchors (must respect)

- `app/modules/auditoria/models.py` → `RegistroAuditoria` (table `auditoria`).
  Columns: `id, fecha (DateTime, indexed), usuario_id (FK, nullable),
  usuario_email, accion, entidad, entidad_id, descripcion, cambios (Text/JSON),
  ip`.
- `app/modules/auditoria/service.py` → `registrar_auditoria(db, usuario, accion,
  entidad, entidad_id, descripcion, cambios=None)` adds a record to the session
  (no commit). Uses `get_client_ip()` which returns `None` outside a request
  (ContextVar default) — safe to reuse from the script to self-audit the purge.
- `app/core/time.py` → `utcnow()` returns **naive UTC**; `auditoria.fecha` stores
  naive UTC. The cutoff MUST be computed with `utcnow()` so the comparison
  matches.
- `app/core/config.py` → `Settings` (pydantic-settings, `.env`-driven). Existing
  `BACKUP_DIR`, `BACKUP_ENCRYPTION_KEY`, `BACKUP_RETENTION_DAYS: int = 30`.
- `scripts/backup_db.py` → precedent for a maintenance CLI: `sys.path` insert,
  `get_settings()`, `Fernet` encryption with `BACKUP_ENCRYPTION_KEY`, cleanup of
  old files, `SystemExit` on missing key / non-SQLite.
- `tests/conftest.py` → async fixtures `db_session` (AsyncSession) and in-memory
  SQLite; records can be inserted with an explicit old `fecha` for testing.

## Global constraints

- **Retention default:** `AUDITORIA_RETENTION_DAYS: int = 1825` (≈5 years, covers
  the DIAN fiscal firmeza window). Overridable via `.env`.
- **Cutoff:** `utcnow() - timedelta(days=AUDITORIA_RETENTION_DAYS)`; purge rows
  with `fecha < cutoff`.
- **Encryption is mandatory:** if `BACKUP_ENCRYPTION_KEY` is empty the script
  aborts with `SystemExit` — never write audit PII to disk in cleartext.
- **Archive location:** `{BACKUP_DIR}/auditoria/auditoria_purga_{YYYY-MM-DD_HHMMSS}.json.enc`.
- **Export format:** JSON array; each record carries all columns; `fecha`
  serialized ISO 8601; `cambios` re-parsed to a nested object (not a JSON string).
- **Export-before-delete, verified:** write the encrypted file, decrypt it back
  in-process and assert it contains exactly N records, and only then run the
  DELETE. If the export or verification fails, no rows are deleted.
- **Self-audited:** after deleting, insert one audit record
  `accion="Purgar", entidad="Auditoria", usuario=None (system)`,
  `descripcion="Archivados y purgados N registros con fecha < {cutoff}"`. This
  record is newer than the cutoff, so it is never purged by its own run.
- **Idempotent / safe on partial failure:** the file write and the DB delete are
  not a single transaction. If the DB commit fails after the file is written, the
  rows remain and a re-run simply re-archives and deletes them (a harmless extra
  archive file may exist). Deletion never happens without a verified archive.
- **Empty case:** if no rows match, print "nada que purgar" and exit 0 without
  creating a file.
- SQLite, single-worker LAN — no locking concerns; new records written during the
  run are `>= cutoff` and unaffected.

## Threat model + mitigations

Attack surface: a **destructive DELETE over the accountability trail**.

- **A02 Cryptographic failures** — the archive may contain PII (emails, client
  data diffs). *Mitigation:* Fernet encryption reusing `BACKUP_ENCRYPTION_KEY`;
  cleartext export is refused (SystemExit when key absent).
- **A09 Logging/monitoring failures** — deleting audit data could erase evidence.
  *Mitigation:* export-before-delete makes it reversible, and the purge action is
  itself recorded in the audit log (who/how-many/up-to-when).
- **Injection** — none: the cutoff comes from config, not from any request; the
  query uses parameterized ORM predicates.
- **Untrusted input** — none: no new network/API surface; retention is an
  operator-set config value.
- **AuthZ** — authorization is filesystem/`.env` level (same trust as
  `backup_db.py`), not an app role — appropriate for a server-admin maintenance
  task and consistent with existing scripts.

Residual risk: a mis-set retention could archive+delete more than intended —
mitigated by the reversible encrypted archive and a conservative 5-year default.

## Scope

~4–5 tasks: config var, core `purge.py` (TDD), CLI wrapper, tests, `.env` docs.
No frontend, no migration (no schema change).
