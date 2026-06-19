import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import Base, get_db
from app.core.limiter import limiter
from app.modules.usuarios.models import Usuario
from app.core.security import get_password_hash

limiter.enabled = False

# Usar SQLite en memoria para pruebas rápidas
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

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
        await db.commit()
        
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c

@pytest_asyncio.fixture(scope="function")
async def auth_headers(client):
    response = await client.post(
        "/api/login/access-token",
        data={"username": "admin@test.com", "password": "testpassword"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
