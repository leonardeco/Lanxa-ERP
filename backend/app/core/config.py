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
    # UVT 2026 = $52.374 (DIAN Res. 000238 de 15-dic-2025). Override vía .env.
    UVT_VALOR: Decimal = Decimal("52374")
    RETEFUENTE_BASE_UVT: Decimal = Decimal("27")   # tope en UVT para retefuente de compras generales
    # #24 redondeo de retenciones sugeridas: half_even (default) | half_up
    RETENCION_REDONDEO: str = "half_even"

    # Seed — usuario administrador inicial (override vía .env en producción)
    SEED_ADMIN_EMAIL: str = "admin@superozonoglobal.com"
    SEED_ADMIN_PASSWORD: str = _DEFAULT_SEED_ADMIN_PASSWORD

    # Datos DEMO (productos/clientes de ejemplo). En blanco por defecto: solo se
    # siembra la config esencial (PUC, parámetros, admin). Poner true SOLO en un
    # entorno de demostración; en producción/uso real déjalo en false.
    SEED_DEMO: bool = False

    # Empresa
    EMPRESA_NIT: str = "901841798-5"
    EMPRESA_RAZON_SOCIAL: str = "TECNOLOGIA E INNOVACION SUPER OZONO S.A.S."
    EMPRESA_CIUDAD: str = "Armenia, Quindio"

    # Facturación electrónica / resolución DIAN (#22) — rellenar en .env cuando
    # la DIAN autorice la numeración (o vía Alegra). Vacío = documento interno.
    DIAN_RESOLUCION_NUMERO: str = ""
    DIAN_RESOLUCION_FECHA: str = ""          # YYYY-MM-DD o texto libre corto
    DIAN_PREFIJO: str = ""
    DIAN_RANGO_DESDE: str = ""
    DIAN_RANGO_HASTA: str = ""
    DIAN_VIGENCIA_HASTA: str = ""           # YYYY-MM-DD

    # Habeas Data Ley 1581 (#23) — texto corto en documentos / UI de consentimiento.
    # Sustituir por el texto legal validado por la empresa (no es asesoría jurídica).
    HABEAS_DATA_TEXTO: str = (
        "El titular autoriza el tratamiento de sus datos personales conforme a la "
        "Ley 1581 de 2012 y políticas de TECNOLOGÍA E INNOVACIÓN SUPER OZONO S.A.S. "
        "para fines comerciales y de facturación. Puede ejercer sus derechos de "
        "habeas data escribiendo a info@superozonoglobal.com."
    )

    # CORS — orígenes permitidos separados por coma
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Alegra (facturacion electronica)
    ALEGRA_EMAIL: str = ""
    ALEGRA_TOKEN: str = ""

    # Backups cifrados Fernet: SQLite (backup_db.py) y/o Postgres (backup_pg.py)
    BACKUP_DIR: str = "C:/SuperOzono-Backups"
    BACKUP_ENCRYPTION_KEY: str = ""
    BACKUP_RETENTION_DAYS: int = 30

    # Auditoría — retención antes de archivar+purgar (#28). ≈5 años cubre la
    # firmeza fiscal DIAN. El archivo exportado se cifra con BACKUP_ENCRYPTION_KEY.
    AUDITORIA_RETENTION_DAYS: int = 1825

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("RETENCION_REDONDEO")
    @classmethod
    def _redondeo_retencion_valido(cls, v: str) -> str:
        modo = (v or "half_even").strip().lower().replace("-", "_")
        if modo not in ("half_even", "half_up"):
            raise ValueError("RETENCION_REDONDEO debe ser 'half_even' o 'half_up'")
        return modo

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
