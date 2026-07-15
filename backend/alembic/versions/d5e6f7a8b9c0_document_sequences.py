"""document_sequences: contadores para numeración concurrente-safe (#12a)

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-15

Tabla de contadores monotónicos por prefijo (SOG-V, SOG-CP, RC, CE, COT, NC, ND).
Sustituye el patrón MAX+1 sin lock en `core/numbering.py`.
"""
from alembic import op
import sqlalchemy as sa

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_sequences",
        sa.Column("prefix", sa.String(length=32), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("prefix"),
    )


def downgrade() -> None:
    op.drop_table("document_sequences")
