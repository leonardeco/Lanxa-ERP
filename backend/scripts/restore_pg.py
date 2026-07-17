"""
Restaura un backup cifrado de PostgreSQL (Fernet + pg_restore).

Uso:
  venv\\Scripts\\python.exe scripts\\restore_pg.py C:\\SuperOzono-Backups\\superozono_pg_....dump.enc

Requisitos:
  - BACKUP_ENCRYPTION_KEY en .env
  - DATABASE_URL (o PG_BACKUP_DATABASE_URL) apuntando al Postgres destino
  - pg_restore en PATH o en Program Files\\PostgreSQL

Por seguridad NO borra la BD actual a ciegas: usa --clean --if-exists en el
dump custom. Detener el ERP (stop.bat) antes de restaurar en producción.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings  # noqa: E402


def _normalize_pg_url(url: str) -> str:
    return re.sub(r"^postgresql\+\w+", "postgresql", url.strip())


def _is_postgres(url: str) -> bool:
    u = url.strip().lower()
    return u.startswith("postgresql") or u.startswith("postgres://")


def _parse_pg_url(url: str) -> dict[str, str | int]:
    raw = _normalize_pg_url(url)
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    parsed = urlparse(raw)
    db = (parsed.path or "").lstrip("/")
    if not db:
        raise SystemExit("URL Postgres sin nombre de base")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 5432,
        "user": unquote(parsed.username or "postgres"),
        "password": unquote(parsed.password or ""),
        "dbname": db,
    }


def _find_pg_restore() -> Path:
    override = os.environ.get("PG_RESTORE")
    if override and Path(override).is_file():
        return Path(override)
    which = shutil.which("pg_restore")
    if which:
        return Path(which)
    roots = [
        Path(r"C:\Program Files\PostgreSQL"),
        Path(r"C:\Program Files (x86)\PostgreSQL"),
    ]
    for root in roots:
        if not root.is_dir():
            continue
        for ver_dir in sorted(root.iterdir(), reverse=True):
            p = ver_dir / "bin" / "pg_restore.exe"
            if p.is_file():
                return p
    raise SystemExit("No se encontro pg_restore. Define PG_RESTORE=ruta\\pg_restore.exe")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: restore_pg.py <ruta-al-backup.dump.enc>")

    backup_path = Path(sys.argv[1])
    if not backup_path.exists():
        raise SystemExit(f"No existe: {backup_path}")

    settings = get_settings()
    if not settings.BACKUP_ENCRYPTION_KEY:
        raise SystemExit("BACKUP_ENCRYPTION_KEY no esta configurada en .env")

    url = (os.environ.get("PG_BACKUP_DATABASE_URL") or settings.DATABASE_URL or "").strip()
    if not _is_postgres(url):
        raise SystemExit(
            "DATABASE_URL no es PostgreSQL. Define PG_BACKUP_DATABASE_URL o cambia DATABASE_URL."
        )

    conn = _parse_pg_url(url)
    fernet = Fernet(settings.BACKUP_ENCRYPTION_KEY.encode())
    try:
        dump_bytes = fernet.decrypt(backup_path.read_bytes())
    except Exception as e:
        raise SystemExit(f"No se pudo descifrar (clave incorrecta o archivo corrupto): {e}") from e

    fd, tmp_name = tempfile.mkstemp(prefix="so_pg_restore_", suffix=".dump")
    os.close(fd)
    tmp_path = Path(tmp_name)
    env = os.environ.copy()
    if conn["password"]:
        env["PGPASSWORD"] = str(conn["password"])

    pg_restore = _find_pg_restore()
    try:
        tmp_path.write_bytes(dump_bytes)
        cmd = [
            str(pg_restore),
            "-h",
            str(conn["host"]),
            "-p",
            str(conn["port"]),
            "-U",
            str(conn["user"]),
            "-d",
            str(conn["dbname"]),
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-acl",
            "--no-password",
            str(tmp_path),
        ]
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
        # pg_restore puede devolver 1 con warnings; 0 = limpio
        if proc.returncode not in (0, 1):
            err = (proc.stderr or proc.stdout or "").strip()
            raise SystemExit(f"pg_restore fallo (code {proc.returncode}): {err[:800]}")
        if proc.returncode == 1:
            print("Aviso: pg_restore termino con warnings (code 1). Revisar si hay objetos faltantes.")
            if proc.stderr:
                print(proc.stderr[:400])
        print(f"Restaurado en Postgres {conn['host']}:{conn['port']}/{conn['dbname']}")
        print("Reinicia el ERP (start.bat) y corre smoke-prod.py")
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
