"""
Super Ozono Global — Database connection (async SQLAlchemy 2.0)
Soporta PostgreSQL (producción/Docker) y SQLite (desarrollo local)
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

# ── Configuración de pool según driver ───────────────────
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict[str, Any] = {
    "echo": settings.DEBUG,
}

if not _is_sqlite:
    # PostgreSQL: pool optimizado para producción
    _engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    **_engine_kwargs,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields a database session.

    Run 3: al abrir, fija `app.tenant_id` (Postgres RLS) al tenant del
    contextvar (default LAN = 1) para que login y rutas públicas vean
    la empresa correcta antes de autenticar.
    """
    from app.core.tenancy import apply_rls_tenant, get_tenant_id

    async with async_session() as session:
        try:
            await apply_rls_tenant(session, get_tenant_id())
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
