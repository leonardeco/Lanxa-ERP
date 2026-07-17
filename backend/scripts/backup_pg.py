"""
Respaldo cifrado de PostgreSQL del ERP (pg_dump + Fernet).

Uso:
  venv\\Scripts\\python.exe scripts\\backup_pg.py

Lee DATABASE_URL de backend\\.env (debe ser postgresql...).
Opcional: variable de entorno PG_BACKUP_DATABASE_URL para respaldar un
Postgres distinto mientras la app sigue en SQLite.

Salida: {BACKUP_DIR}/superozono_pg_YYYY-MM-DD_HHMMSS.dump.enc
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings  # noqa: E402


def _normalize_pg_url(url: str) -> str:
    """postgresql+asyncpg://... → postgresql://..."""
    return re.sub(r"^postgresql\+\w+", "postgresql", url.strip())


def _is_postgres(url: str) -> bool:
    u = url.strip().lower()
    return u.startswith("postgresql") or u.startswith("postgres://")


def _parse_pg_url(url: str) -> dict[str, str | int]:
    raw = _normalize_pg_url(url)
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    parsed = urlparse(raw)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise SystemExit(f"URL no es PostgreSQL: {parsed.scheme}")
    db = (parsed.path or "").lstrip("/")
    if not db:
        raise SystemExit("DATABASE_URL de Postgres sin nombre de base")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 5432,
        "user": unquote(parsed.username or "postgres"),
        "password": unquote(parsed.password or ""),
        "dbname": db,
    }


def _find_pg_bin(name: str) -> Path:
    """Busca pg_dump / pg_restore en PATH o en instalación típica Windows."""
    env_key = "PG_DUMP" if name == "pg_dump" else "PG_RESTORE"
    override = os.environ.get(env_key)
    if override and Path(override).is_file():
        return Path(override)

    which = shutil.which(name)
    if which:
        return Path(which)

    roots = [
        Path(r"C:\Program Files\PostgreSQL"),
        Path(r"C:\Program Files (x86)\PostgreSQL"),
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for ver_dir in sorted(root.iterdir(), reverse=True):
            bin_path = ver_dir / "bin" / f"{name}.exe"
            if bin_path.is_file():
                candidates.append(bin_path)
    if candidates:
        return candidates[0]

    raise SystemExit(
        f"No se encontro {name}. Instala PostgreSQL client tools o define {env_key}=ruta\\{name}.exe"
    )


def _cleanup_old(backup_dir: Path, retention_days: int) -> None:
    cutoff = datetime.now() - timedelta(days=retention_days)
    for f in backup_dir.glob("superozono_pg_*.dump.enc"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()


def main() -> None:
    settings = get_settings()
    if not settings.BACKUP_ENCRYPTION_KEY:
        raise SystemExit("BACKUP_ENCRYPTION_KEY no esta configurada en .env")

    url = (os.environ.get("PG_BACKUP_DATABASE_URL") or settings.DATABASE_URL or "").strip()
    if not _is_postgres(url):
        raise SystemExit(
            "No hay URL Postgres. DATABASE_URL actual no es postgresql "
            "(si usas SQLite en LAN, define PG_BACKUP_DATABASE_URL o migra DATABASE_URL). "
            "Para SQLite usa scripts\\backup_db.py"
        )

    conn = _parse_pg_url(url)
    pg_dump = _find_pg_bin("pg_dump")

    backup_dir = Path(settings.BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    fd, tmp_name = tempfile.mkstemp(prefix="so_pg_", suffix=".dump")
    os.close(fd)
    tmp_path = Path(tmp_name)

    env = os.environ.copy()
    if conn["password"]:
        env["PGPASSWORD"] = str(conn["password"])

    cmd = [
        str(pg_dump),
        "-h",
        str(conn["host"]),
        "-p",
        str(conn["port"]),
        "-U",
        str(conn["user"]),
        "-d",
        str(conn["dbname"]),
        "-Fc",  # custom format (pg_restore)
        "-f",
        str(tmp_path),
        "--no-password",
    ]

    try:
        proc = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            raise SystemExit(f"pg_dump fallo (code {proc.returncode}): {err[:500]}")

        raw = tmp_path.read_bytes()
        if len(raw) < 32:
            raise SystemExit("pg_dump produjo archivo vacio o sospechoso")

        fernet = Fernet(settings.BACKUP_ENCRYPTION_KEY.encode())
        encrypted = fernet.encrypt(raw)
        dest = backup_dir / f"superozono_pg_{timestamp}.dump.enc"
        dest.write_bytes(encrypted)
        _cleanup_old(backup_dir, settings.BACKUP_RETENTION_DAYS)
        print(f"Backup Postgres creado: {dest} ({len(raw)} bytes dump, {len(encrypted)} cifrado)")
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
