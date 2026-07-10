"""usuarios: agregar rol 'Contador' al CHECK constraint ck_usuarios_rol

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-07-10

Recrea el CHECK de `usuarios.rol` para admitir el nuevo rol 'Contador' (área
contable: contabilidad, cartera, reportes; sin gestión de usuarios ni anulación
de ventas/compras). Batch para SQLite; también válido en PostgreSQL.
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

_ROLES_NUEVO = "rol IN ('Admin', 'Administradora', 'Auxiliar', 'Contador')"
_ROLES_VIEJO = "rol IN ('Admin', 'Administradora', 'Auxiliar')"


def upgrade() -> None:
    with op.batch_alter_table("usuarios", schema=None) as batch:
        batch.drop_constraint("ck_usuarios_rol", type_="check")
        batch.create_check_constraint("ck_usuarios_rol", _ROLES_NUEVO)


def downgrade() -> None:
    with op.batch_alter_table("usuarios", schema=None) as batch:
        batch.drop_constraint("ck_usuarios_rol", type_="check")
        batch.create_check_constraint("ck_usuarios_rol", _ROLES_VIEJO)
