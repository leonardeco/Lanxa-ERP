import os
# #33: el validator de config exige override de SEED_ADMIN_PASSWORD cuando
# DEBUG=false. La suite corre con la BD real .env (DEBUG=false), así que se
# provee un valor propio ANTES de importar la app (que instancia Settings).
os.environ.setdefault("SEED_ADMIN_PASSWORD", "test-admin-pass-no-produccion")

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402

from decimal import Decimal  # noqa: E402

from app.main import app  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.limiter import limiter  # noqa: E402
from app.modules.usuarios.models import Usuario  # noqa: E402
from app.modules.contabilidad.models import ParametroTributario  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402

limiter.enabled = False

# Usar SQLite en memoria para pruebas rápidas
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Crear un usuario administrador por defecto para pruebas
    async with TestingSessionLocal() as db:
        admin = Usuario(
            email="admin@test.com",
            nombre_completo="Admin Test",
            rol="Admin",
            hashed_password=get_password_hash("testpassword")
        )
        db.add(admin)
        # Tarifas de retención que el motor de ventas lee (reflejan el seed de producción)
        db.add(ParametroTributario(concepto="Retención en la fuente - compras",
                                   tarifa_valor=Decimal("0.02500"), activo=True))
        db.add(ParametroTributario(concepto="ReteIVA",
                                   tarifa_valor=Decimal("0.15000"), activo=True))
        await db.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with TestingSessionLocal() as session:
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
