"""
Respaldo diario cifrado de la base de datos SQLite del ERP.
Uso: venv\\Scripts\\python.exe scripts\\backup_db.py
Pensado para correr desde el Programador de tareas de Windows.
"""
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings  # noqa: E402


def _sqlite_path_from_url(database_url: str, backend_dir: Path) -> Path:
    if not database_url.startswith("sqlite"):
        raise SystemExit(f"DATABASE_URL no es SQLite ({database_url}); este script no aplica.")
    raw_path = database_url.split("///", 1)[1]
    return (backend_dir / raw_path).resolve()


def _backup_live_db(db_path: Path, tmp_path: Path) -> None:
    """Copia consistente de un SQLite en uso via la API de backup de sqlite3."""
    src_conn = sqlite3.connect(str(db_path))
    dest_conn = sqlite3.connect(str(tmp_path))
    src_conn.backup(dest_conn)
    dest_conn.close()
    src_conn.close()


def _cleanup_old_backups(backup_dir: Path, retention_days: int) -> None:
    cutoff = datetime.now() - timedelta(days=retention_days)
    for f in backup_dir.glob("superozono_*.db.enc"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink()


def main() -> None:
    settings = get_settings()
    if not settings.BACKUP_ENCRYPTION_KEY:
        raise SystemExit("BACKUP_ENCRYPTION_KEY no esta configurada en .env")

    backend_dir = Path(__file__).resolve().parent.parent
    db_path = _sqlite_path_from_url(settings.DATABASE_URL, backend_dir)
    if not db_path.exists():
        raise SystemExit(f"No se encontro la base de datos en {db_path}")

    backup_dir = Path(settings.BACKUP_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    tmp_copy = backup_dir / f"_tmp_{timestamp}.db"
    _backup_live_db(db_path, tmp_copy)

    fernet = Fernet(settings.BACKUP_ENCRYPTION_KEY.encode())
    encrypted = fernet.encrypt(tmp_copy.read_bytes())
    dest_path = backup_dir / f"superozono_{timestamp}.db.enc"
    dest_path.write_bytes(encrypted)
    tmp_copy.unlink()

    _cleanup_old_backups(backup_dir, settings.BACKUP_RETENTION_DAYS)
    print(f"Backup creado: {dest_path}")


if __name__ == "__main__":
    main()
