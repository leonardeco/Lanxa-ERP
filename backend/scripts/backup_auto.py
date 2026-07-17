"""
Backup automatico segun DATABASE_URL (SQLite o PostgreSQL).

Uso (tarea programada recomendada):
  venv\\Scripts\\python.exe scripts\\backup_auto.py

- sqlite...  → backup_db.py  (*.db.enc)
- postgres... → backup_pg.py (*.dump.enc)

Misma BACKUP_ENCRYPTION_KEY / BACKUP_DIR del .env.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    url = (settings.DATABASE_URL or "").strip().lower()
    scripts = Path(__file__).resolve().parent

    if url.startswith("sqlite"):
        print("backup_auto: motor SQLite → backup_db.py")
        runpy.run_path(str(scripts / "backup_db.py"), run_name="__main__")
        return

    if url.startswith("postgres") or url.startswith("postgresql"):
        print("backup_auto: motor PostgreSQL → backup_pg.py")
        runpy.run_path(str(scripts / "backup_pg.py"), run_name="__main__")
        return

    raise SystemExit(
        f"DATABASE_URL no soportada para backup_auto: {settings.DATABASE_URL[:40]}..."
    )


if __name__ == "__main__":
    main()
