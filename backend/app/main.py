"""
Super Ozono Global — ERP Backend (FastAPI)
Punto de entrada principal
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine, async_session, Base
from app.modules.contabilidad.router import router as contabilidad_router
from app.modules.ventas.router import router as ventas_router
from app.modules.usuarios.router import router as usuarios_router
from app.modules.contabilidad.schemas import HealthResponse

# ── Structured Logging ───────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
)
logger = structlog.get_logger()
settings = get_settings()


# ══════════════════════════════════════════════════════════
# LIFESPAN — Startup & Shutdown
# ══════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables + run seeders. Shutdown: dispose engine."""
    logger.info(
        "[START] Iniciando Super Ozono Global ERP",
        version=settings.APP_VERSION,
        empresa=settings.EMPRESA_RAZON_SOCIAL,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[DB] Tablas de base de datos verificadas")

    # Run seeders
    try:
        from seeds.seed import run_seeds
        await run_seeds()
    except Exception as e:
        logger.warning("[WARN] Seeders no ejecutados (posiblemente ya cargados)", error=str(e))

    yield

    # Shutdown
    await engine.dispose()
    logger.info("[STOP] Backend detenido correctamente")


# ══════════════════════════════════════════════════════════
# APP FACTORY
# ══════════════════════════════════════════════════════════

app = FastAPI(
    title="Super Ozono Global — ERP API",
    description=(
        "API REST para el sistema ERP de Super Ozono Global. "
        "Módulos: Contabilidad, Ventas, Inventario, RRHH, Plataformas y Reportes."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Fallback
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ─────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Verifica que la API y la base de datos estén operativas."""
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        version=settings.APP_VERSION,
        empresa="Super Ozono Global",
    )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint con información del sistema."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "empresa": settings.EMPRESA_RAZON_SOCIAL,
        "nit": settings.EMPRESA_NIT,
        "docs": "/docs",
        "health": "/health",
    }


# ── Register Routers ─────────────────────────────────────
app.include_router(usuarios_router, prefix="/api", tags=["Usuarios y Seguridad"])
app.include_router(contabilidad_router)
app.include_router(ventas_router)
