import os
# #33: el validator de config exige override de SEED_ADMIN_PASSWORD cuando
# DEBUG=false. La suite corre con la BD real .env (DEBUG=false), así que se
# provee un valor propio ANTES de importar la app (que instancia Settings).
os.environ.setdefault("SEED_ADMIN_PASSWORD", "test-admin-pass-no-produccion")

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402

from decimal import Decimal  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.limiter import limiter  # noqa: E402
from app.core.tenancy import (  # noqa: E402
    Tenant,
    DEFAULT_TENANT_ID,
    apply_rls_tenant,
    enable_postgres_rls_on_connection,
)
from app.modules.usuarios.models import Usuario  # noqa: E402
from app.modules.contabilidad.models import ParametroTributario  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402

limiter.enabled = False

# La suite corre contra PostgreSQL (Run 1 — Fundación Postgres): es el motor de
# producción/nube y el único que soporta RLS (Runs siguientes). Se toma de
# TEST_DATABASE_URL para que CI/local apunten a su Postgres; el aserto de dialecto
# evita un falso verde si por config cayera a SQLite (spec T3).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/superozono_test",
)

# NullPool: sin reutilización de conexiones entre tests. pytest-asyncio usa un event
# loop por test y asyncpg no admite compartir una conexión entre loops — el pool por
# defecto provoca "another operation is in progress". NullPool abre/cierra por uso.
engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
assert engine.dialect.name == "postgresql", (
    "La suite debe correr en PostgreSQL (spec T3). "
    f"TEST_DATABASE_URL={TEST_DATABASE_URL!r} resolvió al dialecto "
    f"{engine.dialect.name!r}."
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            await apply_rls_tenant(session, DEFAULT_TENANT_ID)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

app.dependency_overrides[get_db] = override_get_db

# El endpoint /health no usa get_db: llama a app.main.async_session directamente (el
# engine de la app). En tests lo apuntamos al engine de test (NullPool) para que use la
# misma BD y no arrastre el problema de conexiones asyncpg reutilizadas entre los event
# loops por-test (el pool por defecto de la app da "Event loop is closed" → degraded).
import app.main as _app_main  # noqa: E402
_app_main.async_session = TestingSessionLocal


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        # Run 3: mismas políticas RLS que la migración (solo Postgres)
        await conn.run_sync(enable_postgres_rls_on_connection)

    # Tenant #1 (Run 2) + admin + tarifas de retención
    async with TestingSessionLocal() as db:
        await apply_rls_tenant(db, DEFAULT_TENANT_ID)
        db.add(Tenant(
            id=DEFAULT_TENANT_ID,
            codigo="superozono",
            razon_social="Super Ozono Test",
            nit="901841798-5",
            activo=True,
        ))
        await db.flush()
        admin = Usuario(
            email="admin@test.com",
            nombre_completo="Admin Test",
            rol="Superusuario",
            hashed_password=get_password_hash("testpassword"),
            tenant_id=DEFAULT_TENANT_ID,
        )
        db.add(admin)
        # Tarifas de retención que el motor de ventas lee (reflejan el seed de producción)
        db.add(ParametroTributario(
            concepto="Retención en la fuente - compras",
            tarifa_valor=Decimal("0.02500"), activo=True,
            tenant_id=DEFAULT_TENANT_ID,
        ))
        db.add(ParametroTributario(
            concepto="ReteIVA",
            tarifa_valor=Decimal("0.15000"), activo=True,
            tenant_id=DEFAULT_TENANT_ID,
        ))
        await db.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with TestingSessionLocal() as session:
        await apply_rls_tenant(session, DEFAULT_TENANT_ID)
        yield session


@pytest_asyncio.fixture(scope="function")
async def client():
    # https en el base_url: el cookie jar de httpx no reenvia cookies "Secure"
    # sobre un esquema http, y el refresh token ahora va con Secure=True.
    # ASGITransport no abre sockets reales, asi que no hace falta TLS de verdad.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver") as c:
        yield c


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client):
    response = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
