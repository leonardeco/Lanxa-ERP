import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.config import get_settings
from app.core.database import Base

# Importar todos los módulos con modelos para que queden registrados en
# Base.metadata — sin esto, autogenerate ve la BD "vacía" y propone drops.
from app.modules.usuarios import models as _usuarios_models  # noqa: F401
from app.modules.contabilidad import models as _contabilidad_models  # noqa: F401
from app.modules.ventas import models as _ventas_models  # noqa: F401
from app.modules.ventas_diarias import models as _ventas_diarias_models  # noqa: F401
from app.modules.compras import models as _compras_models  # noqa: F401
from app.modules.inventario import models as _inventario_models  # noqa: F401
from app.modules.auditoria import models as _auditoria_models  # noqa: F401
from app.core.numbering import DocumentSequence as _document_sequences  # noqa: F401
from app.core.tenancy import Tenant as _tenant_model  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# La URL viene del .env de la app (una sola fuente de verdad), no de alembic.ini
config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite no soporta ALTER TABLE completo — batch mode recrea la tabla
        render_as_batch=url is not None and url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
