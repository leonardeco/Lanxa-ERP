"""roles: Superusuario, Directora, CEO, Contador, Auxiliar Contable

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-07-15

Mapeo de roles legacy:
- Admin → Superusuario
- Administradora → Directora
- Auxiliar → Auxiliar Contable
- Contador se mantiene
- CEO es nuevo (sin filas legacy)

En SQLite el CHECK se valida al UPDATE, así que se recrea la tabla
mapeando roles en el INSERT (mismo patrón que c4d5e6f7a8b9).
"""
from alembic import op
from sqlalchemy import text

revision = "b1c2d3e4f5a6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None

_ROLES_NUEVO = (
    "rol IN ('Superusuario', 'Directora', 'CEO', 'Contador', 'Auxiliar Contable')"
)
_ROLES_VIEJO = "rol IN ('Admin', 'Administradora', 'Auxiliar', 'Contador')"

_MAP_UP = """
CASE rol
  WHEN 'Admin' THEN 'Superusuario'
  WHEN 'Administradora' THEN 'Directora'
  WHEN 'Auxiliar' THEN 'Auxiliar Contable'
  ELSE rol
END
"""

_MAP_DOWN = """
CASE rol
  WHEN 'Superusuario' THEN 'Admin'
  WHEN 'Directora' THEN 'Administradora'
  WHEN 'Auxiliar Contable' THEN 'Auxiliar'
  WHEN 'CEO' THEN 'Auxiliar'
  ELSE rol
END
"""


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _sqlite_recreate(map_expr: str, roles_check: str) -> None:
    """Recrea usuarios con CHECK nuevo y roles ya mapeados (evita IntegrityError)."""
    conn = op.get_bind()
    conn.execute(text("PRAGMA legacy_alter_table=ON"))
    conn.execute(text("PRAGMA foreign_keys=OFF"))
    try:
        conn.execute(text("ALTER TABLE usuarios RENAME TO usuarios_old"))
        conn.execute(
            text(
                f"""
                CREATE TABLE usuarios (
                    id INTEGER NOT NULL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    nombre_completo VARCHAR(255) NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    rol VARCHAR(50) NOT NULL CHECK ({roles_check}),
                    is_active BOOLEAN NOT NULL,
                    tenant_id INTEGER DEFAULT 1 NOT NULL,
                    CONSTRAINT uq_usuarios_tenant_email UNIQUE (tenant_id, email)
                )
                """
            )
        )
        conn.execute(
            text(
                f"""
                INSERT INTO usuarios (
                    id, email, nombre_completo, hashed_password, rol, is_active, tenant_id
                )
                SELECT
                    id, email, nombre_completo, hashed_password,
                    {map_expr},
                    is_active,
                    COALESCE(tenant_id, 1)
                FROM usuarios_old
                """
            )
        )
        conn.execute(text("DROP TABLE usuarios_old"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_usuarios_id ON usuarios (id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_usuarios_email ON usuarios (email)"))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_usuarios_tenant_id ON usuarios (tenant_id)")
        )
    finally:
        conn.execute(text("PRAGMA foreign_keys=ON"))


def upgrade() -> None:
    if _is_sqlite():
        _sqlite_recreate(_MAP_UP, _ROLES_NUEVO)
        return

    # PostgreSQL: se puede renombrar y luego cambiar el CHECK
    op.execute(text("UPDATE usuarios SET rol = 'Superusuario' WHERE rol = 'Admin'"))
    op.execute(text("UPDATE usuarios SET rol = 'Directora' WHERE rol = 'Administradora'"))
    op.execute(text("UPDATE usuarios SET rol = 'Auxiliar Contable' WHERE rol = 'Auxiliar'"))
    with op.batch_alter_table("usuarios", schema=None) as batch:
        try:
            batch.drop_constraint("ck_usuarios_rol", type_="check")
        except (KeyError, ValueError):
            pass
        batch.create_check_constraint("ck_usuarios_rol", _ROLES_NUEVO)


def downgrade() -> None:
    if _is_sqlite():
        _sqlite_recreate(_MAP_DOWN, _ROLES_VIEJO)
        return

    op.execute(text("UPDATE usuarios SET rol = 'Admin' WHERE rol = 'Superusuario'"))
    op.execute(text("UPDATE usuarios SET rol = 'Administradora' WHERE rol = 'Directora'"))
    op.execute(text("UPDATE usuarios SET rol = 'Auxiliar' WHERE rol = 'Auxiliar Contable'"))
    op.execute(text("UPDATE usuarios SET rol = 'Auxiliar' WHERE rol = 'CEO'"))
    with op.batch_alter_table("usuarios", schema=None) as batch:
        try:
            batch.drop_constraint("ck_usuarios_rol", type_="check")
        except (KeyError, ValueError):
            pass
        batch.create_check_constraint("ck_usuarios_rol", _ROLES_VIEJO)
