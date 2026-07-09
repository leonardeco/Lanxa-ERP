# Implementation Plan — #28 Audit log purge/archival

**Goal:** Archive-then-purge audit records older than a configurable retention
(default ≈5 years) via a standalone script backed by a testable async module
function; export is encrypted (Fernet) and verified before any delete, and the
purge self-audits.

**Architecture:** Core logic in `app/modules/auditoria/purge.py`
(`purgar_auditoria`), thin CLI wrapper `scripts/purge_auditoria.py` mirroring
`scripts/backup_db.py`. No API/UI/migration.

**Tech stack:** Python 3.13, FastAPI, async SQLAlchemy 2.0, pydantic-settings,
cryptography (Fernet), pytest + pytest-asyncio.

**Spec:** `docs/hydraia/specs/2026-07-09-purga-auditoria-design.md`

**Global constraints (copied from spec):**
- Retention default `AUDITORIA_RETENTION_DAYS = 1825`, overridable via `.env`.
- Cutoff `= utcnow() - timedelta(days=AUDITORIA_RETENTION_DAYS)`; purge `fecha < cutoff`.
- Encryption mandatory: no key → abort, never write PII cleartext.
- Archive: `{BACKUP_DIR}/auditoria/auditoria_purga_{ts}.json.enc`.
- Export-before-delete, verified by decrypt+count; self-audited purge record.
- Empty case: no file, exit 0.

## File structure

| File | Responsibility |
|---|---|
| `backend/app/core/config.py` (modify) | add `AUDITORIA_RETENTION_DAYS` |
| `backend/app/modules/auditoria/purge.py` (create) | `purgar_auditoria()` core logic |
| `backend/tests/test_purge_auditoria.py` (create) | async TDD coverage |
| `backend/scripts/purge_auditoria.py` (create) | CLI wrapper (Task Scheduler) |
| `.env.example`, `.env.produccion` (modify) | document the new var |
| `PENDIENTES.md`, `DOCUMENTACION.md`, `BITACORA.md`, `DESPLIEGUE.md` (modify) | close-out docs |

Working directory for all commands: `backend/` (activate `venv`).

---

## Task 1 — Config var `AUDITORIA_RETENTION_DAYS`

**Files:** Modify `backend/app/core/config.py`, `.env.example`, `.env.produccion`.

In `config.py`, find the unique anchor line:
```
    BACKUP_RETENTION_DAYS: int = 30
```
Insert immediately after it:
```
    # Auditoría — retención antes de archivar+purgar (#28). ≈5 años cubre la
    # firmeza fiscal DIAN. El archivo exportado se cifra con BACKUP_ENCRYPTION_KEY.
    AUDITORIA_RETENTION_DAYS: int = 1825
```

In both `.env.example` and `.env.produccion`, find the `BACKUP_RETENTION_DAYS`
line and add after it:
```
# Auditoría: días a conservar antes de archivar+purgar el log (#28). 1825 ≈ 5 años.
AUDITORIA_RETENTION_DAYS=1825
```
(If a file has no `BACKUP_RETENTION_DAYS` line, add the block near the other
BACKUP_* vars.)

**Verify:** `grep -c AUDITORIA_RETENTION_DAYS backend/app/core/config.py` → `1`.

---

## Task 2 — Core module `purge.py` + tests (TDD)

**Files:** Create `backend/app/modules/auditoria/purge.py`,
`backend/tests/test_purge_auditoria.py`.

**Consumes:** `app.core.time.utcnow`, `app.modules.auditoria.models.RegistroAuditoria`,
`app.modules.auditoria.service.registrar_auditoria` (adds a record, no commit;
`get_client_ip()` returns None outside a request).
**Produces:** `purgar_auditoria(db, corte, archive_dir, encryption_key) -> ResultadoPurga`
and `ResultadoPurga(registros: int, archivo: Path | None, corte: datetime)`.

### Step 2a — write the test first (expect fail: module missing)

Create `backend/tests/test_purge_auditoria.py` verbatim:
```python
"""
Purga/archivado del log de auditoría (#28): archiva cifrado y borra los
registros anteriores al corte de retención, deja el evento auditado.
"""
import json
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select, func

from app.core.time import utcnow
from app.modules.auditoria.models import RegistroAuditoria
from app.modules.auditoria.purge import purgar_auditoria

RETENCION = 1825


def _make_registro(dias_atras: int, accion="Crear", entidad="Producto"):
    return RegistroAuditoria(
        fecha=utcnow() - timedelta(days=dias_atras),
        usuario_id=None,
        usuario_email="viejo@test.com",
        accion=accion,
        entidad=entidad,
        entidad_id=1,
        descripcion=f"registro de hace {dias_atras} dias",
        cambios=json.dumps({"precio": {"antes": "1", "despues": "2"}}),
        ip="127.0.0.1",
    )


@pytest.mark.asyncio
async def test_purga_borra_viejos_conserva_recientes(db_session, tmp_path):
    key = Fernet.generate_key().decode()
    db_session.add(_make_registro(2000))
    db_session.add(_make_registro(1900))
    db_session.add(_make_registro(10))
    await db_session.commit()

    corte = utcnow() - timedelta(days=RETENCION)
    resultado = await purgar_auditoria(db_session, corte, tmp_path, key)

    assert resultado.registros == 2
    assert resultado.archivo is not None and resultado.archivo.exists()

    restantes = (await db_session.execute(select(RegistroAuditoria))).scalars().all()
    assert sum(1 for r in restantes if r.accion == "Crear") == 1
    purga = next(r for r in restantes if r.accion == "Purgar")
    assert purga.entidad == "Auditoria"
    assert "2 registros" in purga.descripcion


@pytest.mark.asyncio
async def test_archivo_cifrado_descifra_a_los_registros(db_session, tmp_path):
    key = Fernet.generate_key().decode()
    db_session.add(_make_registro(2000))
    await db_session.commit()

    corte = utcnow() - timedelta(days=RETENCION)
    resultado = await purgar_auditoria(db_session, corte, tmp_path, key)

    contenido = Fernet(key.encode()).decrypt(resultado.archivo.read_bytes())
    datos = json.loads(contenido)
    assert len(datos) == 1
    assert datos[0]["usuario_email"] == "viejo@test.com"
    assert datos[0]["cambios"]["precio"]["despues"] == "2"


@pytest.mark.asyncio
async def test_sin_registros_no_crea_archivo(db_session, tmp_path):
    db_session.add(_make_registro(10))
    await db_session.commit()

    corte = utcnow() - timedelta(days=RETENCION)
    resultado = await purgar_auditoria(db_session, corte, tmp_path, encryption_key="")

    assert resultado.registros == 0
    assert resultado.archivo is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_falta_clave_aborta_sin_borrar(db_session, tmp_path):
    db_session.add(_make_registro(2000))
    await db_session.commit()

    corte = utcnow() - timedelta(days=RETENCION)
    with pytest.raises(ValueError):
        await purgar_auditoria(db_session, corte, tmp_path, encryption_key="")

    total = (await db_session.execute(
        select(func.count()).select_from(RegistroAuditoria))).scalar()
    assert total == 1
```
Run (expect ImportError/fail): `cd backend && venv/Scripts/python.exe -m pytest tests/test_purge_auditoria.py -q`

### Step 2b — implement `purge.py`

Create `backend/app/modules/auditoria/purge.py` verbatim:
```python
"""
Archivado y purga del log de auditoría (#28).

Exporta a un archivo JSON cifrado los registros anteriores al corte de
retención, verifica el archivo, y solo entonces los borra — dejando el propio
evento de purga registrado en la auditoría. Usado por scripts/purge_auditoria.py
(manual o Programador de tareas).

Idempotente/seguro ante fallo parcial: la escritura del archivo y el DELETE no
son una sola transacción; si el commit falla tras escribir el archivo, las filas
quedan y una nueva corrida las re-archiva y borra. El borrado nunca ocurre sin un
archivo verificado.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.modules.auditoria.models import RegistroAuditoria
from app.modules.auditoria.service import registrar_auditoria


@dataclass
class ResultadoPurga:
    registros: int
    archivo: Path | None
    corte: datetime


def _registro_a_dict(r: RegistroAuditoria) -> dict:
    return {
        "id": r.id,
        "fecha": r.fecha.isoformat() if r.fecha else None,
        "usuario_id": r.usuario_id,
        "usuario_email": r.usuario_email,
        "accion": r.accion,
        "entidad": r.entidad,
        "entidad_id": r.entidad_id,
        "descripcion": r.descripcion,
        "cambios": json.loads(r.cambios) if r.cambios else None,
        "ip": r.ip,
    }


async def purgar_auditoria(
    db: AsyncSession,
    corte: datetime,
    archive_dir: Path,
    encryption_key: str,
) -> ResultadoPurga:
    """Archiva (cifrado) y borra los registros de auditoría con fecha < corte.

    Si no hay registros, no crea archivo y devuelve registros=0. Lanza
    ValueError si falta la clave de cifrado cuando sí hay algo que archivar.
    """
    rows = (
        await db.execute(
            select(RegistroAuditoria)
            .where(RegistroAuditoria.fecha < corte)
            .order_by(RegistroAuditoria.fecha, RegistroAuditoria.id)
        )
    ).scalars().all()

    if not rows:
        return ResultadoPurga(registros=0, archivo=None, corte=corte)

    if not encryption_key:
        raise ValueError(
            "Se requiere BACKUP_ENCRYPTION_KEY para cifrar el archivo de "
            "auditoría antes de purgar; abortando sin borrar nada."
        )

    datos = [_registro_a_dict(r) for r in rows]
    payload = json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8")

    fernet = Fernet(encryption_key.encode())
    cifrado = fernet.encrypt(payload)

    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = utcnow().strftime("%Y-%m-%d_%H%M%S")
    destino = archive_dir / f"auditoria_purga_{ts}.json.enc"
    destino.write_bytes(cifrado)

    # Verificar el archivo antes de borrar: descifrar y contar.
    verificado = json.loads(fernet.decrypt(destino.read_bytes()).decode("utf-8"))
    if len(verificado) != len(rows):
        raise RuntimeError(
            f"Verificacion del archivo fallo: esperados {len(rows)}, "
            f"el archivo tiene {len(verificado)}. No se borro nada."
        )

    await db.execute(
        delete(RegistroAuditoria).where(RegistroAuditoria.fecha < corte)
    )

    registrar_auditoria(
        db,
        usuario=None,
        accion="Purgar",
        entidad="Auditoria",
        entidad_id=None,
        descripcion=(
            f"Archivados y purgados {len(rows)} registros con fecha < "
            f"{corte.isoformat()} -> {destino.name}"
        ),
    )
    await db.commit()

    return ResultadoPurga(registros=len(rows), archivo=destino, corte=corte)
```
Run (expect pass): `cd backend && venv/Scripts/python.exe -m pytest tests/test_purge_auditoria.py -q`
Commit both files.

---

## Task 3 — CLI wrapper `scripts/purge_auditoria.py`

**Files:** Create `backend/scripts/purge_auditoria.py`.
**Consumes:** `app.core.config.get_settings`, `app.core.database.async_session`,
`app.core.time.utcnow`, `app.modules.auditoria.purge.purgar_auditoria`.

Create verbatim:
```python
"""
Archiva (cifrado) y purga los registros de auditoría anteriores al periodo de
retención (#28). Espejo operativo de scripts/backup_db.py — pensado para el
Programador de tareas de Windows.

Uso: venv\\Scripts\\python.exe scripts\\purge_auditoria.py
"""
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings          # noqa: E402
from app.core.database import async_session        # noqa: E402
from app.core.time import utcnow                    # noqa: E402
from app.modules.auditoria.purge import purgar_auditoria  # noqa: E402


async def _run() -> None:
    settings = get_settings()
    corte = utcnow() - timedelta(days=settings.AUDITORIA_RETENTION_DAYS)
    archive_dir = Path(settings.BACKUP_DIR) / "auditoria"

    async with async_session() as db:
        resultado = await purgar_auditoria(
            db, corte, archive_dir, settings.BACKUP_ENCRYPTION_KEY
        )

    if resultado.registros == 0:
        print(
            f"Nada que purgar (retencion {settings.AUDITORIA_RETENTION_DAYS} "
            f"dias, corte {corte.date()})."
        )
    else:
        print(f"Purgados {resultado.registros} registros -> {resultado.archivo}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
```
**Verify:** from `backend/` run `venv/Scripts/python.exe scripts/purge_auditoria.py`.
On the current (young) dev DB expect: `Nada que purgar (...)` and exit 0, with no
`auditoria/` folder created under BACKUP_DIR. Commit.

---

## Task 4 — Close-out docs

**Files:** Modify `PENDIENTES.md`, `DOCUMENTACION.md`, `BITACORA.md`, `DESPLIEGUE.md`.

- `PENDIENTES.md`: remove the `28 — Purga/archivado del log de auditoría` bullet
  from 🔵 Nice-to-have; bump the revision note.
- `DOCUMENTACION.md`: add a completed-item row (section 13) dated 2026-07-09:
  "#28 Purga/archivado del log de auditoría — script `scripts/purge_auditoria.py`,
  retención `AUDITORIA_RETENTION_DAYS` (5 años), archivo cifrado verificado,
  purga auto-auditada."
- `BITACORA.md`: append a session entry for 2026-07-09 describing the change.
- `DESPLIEGUE.md`: add a short note under maintenance: schedule
  `scripts\purge_auditoria.py` in Windows Task Scheduler (e.g. monthly), requires
  `BACKUP_ENCRYPTION_KEY`; archives land in `{BACKUP_DIR}\auditoria\`.

**Verify:** `grep -c "purge_auditoria" DESPLIEGUE.md` → `>=1`;
`grep -c "#28" DOCUMENTACION.md` → `>=1`.

---

## QA acceptance criteria (traceability)

- AC1: records older than retention are deleted → `test_purga_borra_viejos_conserva_recientes`.
- AC2: recent records are kept → same test.
- AC3: archive is encrypted and round-trips to the exact records → `test_archivo_cifrado_descifra_a_los_registros`.
- AC4: no records → no file, exit 0 → `test_sin_registros_no_crea_archivo`.
- AC5: missing key with rows present → abort, nothing deleted → `test_falta_clave_aborta_sin_borrar`.
- AC6: the purge is itself audited → `test_purga_borra_viejos_conserva_recientes`.
