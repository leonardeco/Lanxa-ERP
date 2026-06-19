"""
Agrega un CHECK constraint sobre usuarios.rol en una BD SQLite ya existente.

SQLite no soporta ALTER TABLE ADD CONSTRAINT, asi que se recrea la tabla
(rename -> create con el constraint -> copiar datos -> drop -> recrear indices).
Bases de datos nuevas ya nacen con el constraint via Base.metadata.create_all()
(ver app/modules/usuarios/models.py) - este script es solo para la BD real que
ya existia antes de agregarlo.

Uso: venv\\Scripts\\python.exe scripts\\migrate_rol_constraint.py
Idempotente: si el constraint ya esta, no hace nada.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings  # noqa: E402
from app.modules.usuarios.models import ROLES_VALIDOS  # noqa: E402


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
        raise SystemExit(f"No se encontro la base de datos en {db_path}")

    conn = sqlite3.connect(str(db_path))

    existing = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='usuarios'"
    ).fetchone()
    if not existing:
        print("No existe la tabla 'usuarios' todavia (BD nueva) - nada que migrar.")
        conn.close()
        return
    if "CHECK" in existing[0] and "rol" in existing[0]:
        print("La tabla 'usuarios' ya tiene el constraint de rol. Nada que hacer.")
        conn.close()
        return

    roles_sql = ", ".join(repr(r) for r in ROLES_VALIDOS)

    # legacy_alter_table=ON evita que SQLite reescriba automaticamente las
    # FOREIGN KEY de OTRAS tablas (refresh_tokens, movimientos_inventario,
    # pagos, etc.) para que apunten a "usuarios_old" al renombrar. Sin esto,
    # esas tablas quedan referenciando una tabla que termina no existiendo.
    conn.execute("PRAGMA legacy_alter_table=ON")
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.execute("BEGIN")
        conn.execute("ALTER TABLE usuarios RENAME TO usuarios_old")
        conn.execute(f"""
            CREATE TABLE usuarios (
                id INTEGER NOT NULL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                nombre_completo VARCHAR(255) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                rol VARCHAR(50) NOT NULL CHECK (rol IN ({roles_sql})),
                is_active BOOLEAN NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO usuarios (id, email, nombre_completo, hashed_password, rol, is_active)
            SELECT id, email, nombre_completo, hashed_password, rol, is_active FROM usuarios_old
        """)
        conn.execute("DROP TABLE usuarios_old")
        conn.execute("CREATE INDEX ix_usuarios_id ON usuarios (id)")
        conn.execute("CREATE UNIQUE INDEX ix_usuarios_email ON usuarios (email)")

        broken_fk_tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%usuarios_old%'"
        ).fetchall()
        if broken_fk_tables:
            raise RuntimeError(
                f"legacy_alter_table no evito la reescritura de FKs en: {broken_fk_tables}. Abortando."
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.close()

    # Verificacion final con una conexion nueva (limpia la cache de esquema)
    verify_conn = sqlite3.connect(str(db_path))
    verify_conn.execute("PRAGMA foreign_keys=ON")
    fk_problems = verify_conn.execute("PRAGMA foreign_key_check").fetchall()
    integrity = verify_conn.execute("PRAGMA integrity_check").fetchall()
    verify_conn.close()
    if fk_problems or integrity != [("ok",)]:
        raise RuntimeError(f"Verificacion post-migracion fallo. FK: {fk_problems}, integrity: {integrity}")

    print(f"Migracion completada: usuarios.rol ahora exige uno de {ROLES_VALIDOS}.")


if __name__ == "__main__":
    main()
