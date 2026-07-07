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
from app.core.logging_config import configurar_logging
from app.modules.contabilidad.router import router as contabilidad_router
from app.modules.ventas.router import router as ventas_router
from app.modules.usuarios.router import router as usuarios_router
from app.modules.alegra.router import router as alegra_router
from app.modules.compras.router import router as compras_router
from app.modules.inventario.router import router as inventario_router
from app.modules.reportes.router import router as reportes_router
from app.modules.auditoria.router import router as auditoria_router
from app.modules.auditoria.context import set_client_ip
from app.modules.contabilidad.schemas import HealthResponse

# ── Logging: consola + archivo rotado backend/logs/erp.log ──
settings = get_settings()
configurar_logging(debug=settings.DEBUG)
logger = structlog.get_logger("erp")


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

    # Esquema de BD (#11): en desarrollo create_all agiliza el arranque; en
    # producción el esquema lo gobierna únicamente Alembic (alembic upgrade
    # head, ver DESPLIEGUE.md) — antes convivían y el que corriera primero
    # ganaba el día que discreparan.
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[DB] Tablas verificadas con create_all (solo desarrollo)")
    else:
        logger.info("[DB] Producción: esquema gobernado por Alembic (alembic upgrade head)")

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
    # SEC-001: la documentación interactiva solo se expone en desarrollo.
    # Con DEBUG=false (producción) /docs, /redoc y /openapi.json devuelven 404.
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Rate limiting ────────────────────────────────────────
# Solo usamos el decorador @limiter.limit() por endpoint (login), no default_limits
# globales, así que SlowAPIMiddleware no hace falta. De hecho rompe escrituras async
# a la BD (BaseHTTPMiddleware + greenlet de SQLAlchemy no son compatibles) — no
# agregarlo de nuevo sin probar primero un INSERT real a través de la API.
app.state.limiter = limiter
# slowapi tipa su handler como (Request, RateLimitExceeded) y Starlette espera
# (Request, Exception) — incompatibilidad conocida de la libreria, sin efecto real.
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security headers ─────────────────────────────────────
# Middleware ASGI puro (no BaseHTTPMiddleware — ver nota de rate limiting arriba:
# BaseHTTPMiddleware rompe las escrituras async de SQLAlchemy).
class SecurityHeadersMiddleware:
    _HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"referrer-policy", b"same-origin"),
        # HSTS solo tiene efecto sobre HTTPS (uvicorn sirve TLS con la CA local)
        (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    ]

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_con_headers(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"].extend(self._HEADERS)
            await send(message)

        await self.app(scope, receive, send_con_headers)


app.add_middleware(SecurityHeadersMiddleware)


# ── IP del cliente para auditoría (#32) ──────────────────
# Middleware ASGI puro: fija la IP en un ContextVar al inicio del request para
# que registrar_auditoria() la registre sin pasar el Request por cada endpoint.
# (BaseHTTPMiddleware rompe las escrituras async de SQLAlchemy — ver arriba.)
class ClientIPMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            ip = None
            # X-Forwarded-For (primer salto) si algún día hay proxy; si no, el peer directo
            for name, value in scope.get("headers", []):
                if name == b"x-forwarded-for":
                    ip = value.decode("latin-1").split(",")[0].strip()
                    break
            if not ip and scope.get("client"):
                ip = scope["client"][0]
            set_client_ip(ip)
        await self.app(scope, receive, send)


app.add_middleware(ClientIPMiddleware)


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
    """Root endpoint. SEC-007: en producción no expone versión ni datos fiscales."""
    if settings.DEBUG:
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "empresa": settings.EMPRESA_RAZON_SOCIAL,
            "nit": settings.EMPRESA_NIT,
            "docs": "/docs",
            "health": "/health",
        }
    return {"status": "online"}


# ── Register Routers ─────────────────────────────────────
app.include_router(usuarios_router, prefix="/api", tags=["Usuarios y Seguridad"])
app.include_router(contabilidad_router)
app.include_router(ventas_router)
app.include_router(alegra_router)
app.include_router(compras_router)
app.include_router(inventario_router)
app.include_router(reportes_router)
app.include_router(auditoria_router)
