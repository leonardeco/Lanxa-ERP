"""cliente habeas_data_aceptado y habeas_data_fecha (Ley 1581)

Revision ID: c6d7e8f9a0b1
Revises: b1c2d3e4f5a6
Create Date: 2026-07-17

Campos de consentimiento Habeas Data en clientes (#23).
"""
from alembic import op
import sqlalchemy as sa

revision = "c6d7e8f9a0b1"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("clientes") as batch:
        batch.add_column(
            sa.Column(
                "habeas_data_aceptado",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.add_column(
            sa.Column("habeas_data_fecha", sa.DateTime(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("clientes") as batch:
        batch.drop_column("habeas_data_fecha")
        batch.drop_column("habeas_data_aceptado")
