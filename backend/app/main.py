"""
Super Ozono Global — ERP Backend (FastAPI)
Punto de entrada principal
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from sqlalchemy import text
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import get_settings
from app.core.database import engine, async_session, Base
from app.core.limiter import limiter
from app.modules.contabilidad.router import router as contabilidad_router
from app.modules.ventas.router import router as ventas_router
from app.modules.usuarios.router import router as usuarios_router
from app.modules.alegra.router import router as alegra_router
from app.modules.compras.router import router as compras_router
from app.modules.inventario.router import router as inventario_router
from app.modules.reportes.router import router as reportes_router
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

# ── Rate limiting ────────────────────────────────────────
# Solo usamos el decorador @limiter.limit() por endpoint (login), no default_limits
# globales, así que SlowAPIMiddleware no hace falta. De hecho rompe escrituras async
# a la BD (BaseHTTPMiddleware + greenlet de SQLAlchemy no son compatibles) — no
# agregarlo de nuevo sin probar primero un INSERT real a través de la API.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
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
app.include_router(alegra_router)
app.include_router(compras_router)
app.include_router(inventario_router)
app.include_router(reportes_router)
