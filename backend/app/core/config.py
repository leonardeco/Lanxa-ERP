"""
Super Ozono Global -- ERP Backend Configuration
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_HOURS: int = 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # App
    DEBUG: bool = False
    APP_NAME: str = "Super Ozono Global ERP"
    APP_VERSION: str = "0.2.0"

    # Empresa
    EMPRESA_NIT: str = "901841798-5"
    EMPRESA_RAZON_SOCIAL: str = "TECNOLOGIA E INNOVACION SUPER OZONO S.A.S."
    EMPRESA_CIUDAD: str = "Armenia, Quindio"

    # CORS — orígenes permitidos separados por coma
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Alegra (facturacion electronica)
    ALEGRA_EMAIL: str = ""
    ALEGRA_TOKEN: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
