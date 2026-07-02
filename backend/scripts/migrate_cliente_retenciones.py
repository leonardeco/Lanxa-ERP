"""
Agrega las columnas de perfil tributario a la tabla `clientes` en una BD SQLite
ya existente (retiene_fuente, retiene_iva, retiene_ica, tarifa_reteica).

SQLite sí soporta ALTER TABLE ADD COLUMN, así que basta con agregarlas si faltan.
Bases de datos nuevas ya nacen con estas columnas vía Base.metadata.create_all()
(ver app/modules/ventas/models.py). Este script es solo para la BD real previa.

Uso: venv\\Scripts\\python.exe scripts\\migrate_cliente_retenciones.py
Idempotente: si las columnas ya existen, no hace nada.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings  # noqa: E402

# columna -> definición SQL (con default para las filas existentes)
_COLUMNS = {
    "retiene_fuente": "BOOLEAN DEFAULT 0",
    "retiene_iva": "BOOLEAN DEFAULT 0",
    "retiene_ica": "BOOLEAN DEFAULT 0",
    "tarifa_reteica": "NUMERIC(6, 3)",
}


def _sqlite_path(database_url: str, backend_dir: Path) -> Path:
    if not database_url.startswith("sqlite"):
        raise SystemExit(f"DATABASE_URL no es SQLite ({database_url}); este script no aplica.")
    raw_path = database_url.split("///", 1)[1]
    return (backend_dir / raw_path).resolve()


def main() -> None:
    settings = get_settings()
    backend_dir = Path(__file__).resolve().parent.parent
    db_path = _sqlite_path(settings.DATABASE_URL, backend_dir)
    if not db_path.exists():
        raise SystemExit(f"No se encontró la base de datos en {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        tabla = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clientes'"
        ).fetchone()
        if not tabla:
            print("No existe la tabla 'clientes' todavía (BD nueva) - nada que migrar.")
            return

        existentes = {row[1] for row in conn.execute("PRAGMA table_info(clientes)").fetchall()}
        agregadas = []
        for col, definicion in _COLUMNS.items():
            if col not in existentes:
                conn.execute(f"ALTER TABLE clientes ADD COLUMN {col} {definicion}")
                agregadas.append(col)
        conn.commit()

        if agregadas:
            print(f"Migración completada: columnas agregadas a 'clientes': {agregadas}")
        else:
            print("La tabla 'clientes' ya tiene las columnas de retención. Nada que hacer.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
