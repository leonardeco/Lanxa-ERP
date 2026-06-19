"""
Restaura un backup cifrado de la base de datos SQLite del ERP.
Uso: venv\\Scripts\\python.exe scripts\\restore_db.py <ruta-al-backup.db.enc>

Sobreescribe backend\\superozono.db. Antes de hacerlo, guarda una copia
de la base de datos actual junto a si misma con sufijo .bak-<fecha>.
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Uso: restore_db.py <ruta-al-backup.db.enc>")

    backup_path = Path(sys.argv[1])
    if not backup_path.exists():
        raise SystemExit(f"No existe: {backup_path}")

    settings = get_settings()
    if not settings.BACKUP_ENCRYPTION_KEY:
        raise SystemExit("BACKUP_ENCRYPTION_KEY no esta configurada en .env")

    fernet = Fernet(settings.BACKUP_ENCRYPTION_KEY.encode())
    decrypted = fernet.decrypt(backup_path.read_bytes())

    backend_dir = Path(__file__).resolve().parent.parent
    raw_path = settings.DATABASE_URL.split("///", 1)[1]
    db_path = (backend_dir / raw_path).resolve()

    if db_path.exists():
        safety_copy = db_path.with_name(db_path.name + f".bak-{datetime.now():%Y%m%d_%H%M%S}")
        shutil.copy2(db_path, safety_copy)
        print(f"Copia de seguridad de la BD actual: {safety_copy}")

    db_path.write_bytes(decrypted)
    print(f"Restaurado en: {db_path}")


if __name__ == "__main__":
    main()
