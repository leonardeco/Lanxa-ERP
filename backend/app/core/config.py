"""
Super Ozono Global -- ERP Backend Configuration
"""

from decimal import Decimal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Contraseña por defecto del admin sembrado. Es pública (vive en el repo), así
# que en producción DEBE sobrescribirse por .env — el validator lo exige.
_DEFAULT_SEED_ADMIN_PASSWORD = "Admin2026!"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str
    # SEC-004: access token de vida corta — la sesión larga la sostiene el
    # refresh token (rotado, revocable). Antes era ACCESS_TOKEN_EXPIRE_HOURS=1.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # App
    DEBUG: bool = False
    APP_NAME: str = "Super Ozono Global ERP"
    APP_VERSION: str = "0.3.0"

    # Retenciones en ventas — VERIFICAR/ACTUALIZAR con el contador cada año.
    # La aplicabilidad depende del perfil del cliente (flags retiene_*); estos son
    # los topes/valores base. Las tarifas viven en ParametroTributario.
    UVT_VALOR: Decimal = Decimal("49799")          # UVT vigente (placeholder — actualizar por año)
    RETEFUENTE_BASE_UVT: Decimal = Decimal("27")   # tope en UVT para retefuente de compras generales

    # Seed — usuario administrador inicial (override vía .env en producción)
    SEED_ADMIN_EMAIL: str = "admin@superozonoglobal.com"
    SEED_ADMIN_PASSWORD: str = _DEFAULT_SEED_ADMIN_PASSWORD

    # Empresa
    EMPRESA_NIT: str = "901841798-5"
    EMPRESA_RAZON_SOCIAL: str = "TECNOLOGIA E INNOVACION SUPER OZONO S.A.S."
    EMPRESA_CIUDAD: str = "Armenia, Quindio"

    # CORS — orígenes permitidos separados por coma
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Alegra (facturacion electronica)
    ALEGRA_EMAIL: str = ""
    ALEGRA_TOKEN: str = ""

    # Backups (solo SQLite)
    BACKUP_DIR: str = "C:/SuperOzono-Backups"
    BACKUP_ENCRYPTION_KEY: str = ""
    BACKUP_RETENTION_DAYS: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _cors_sin_wildcard_en_produccion(cls, v: str, info) -> str:
        # SEC-006: con credenciales habilitadas, un wildcard permitiría a
        # cualquier sitio hacer requests autenticados desde el navegador.
        if not info.data.get("DEBUG", False) and "*" in v:
            raise ValueError(
                "CORS_ORIGINS no admite '*' en producción (DEBUG=false) — "
                "listar los orígenes exactos separados por coma"
            )
        return v

    @field_validator("SEED_ADMIN_PASSWORD")
    @classmethod
    def _seed_admin_no_default_en_produccion(cls, v: str, info) -> str:
        # #33: la contraseña por defecto es pública (está en el repo). En
        # producción (DEBUG=false) obliga a sobrescribirla por .env, para que
        # nadie despliegue con la clave conocida por accidente.
        if not info.data.get("DEBUG", False) and v == _DEFAULT_SEED_ADMIN_PASSWORD:
            raise ValueError(
                "SEED_ADMIN_PASSWORD usa el valor por defecto (público en el "
                "repo). Define uno propio en el .env del servidor antes de "
                "desplegar con DEBUG=false."
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    # DATABASE_URL y SECRET_KEY llegan por .env / variables de entorno
    return Settings()  # type: ignore[call-arg]
