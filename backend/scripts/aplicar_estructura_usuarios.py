"""
Aplica la estructura de usuarios de negocio en la BD LAN (SQLite).

Roles:
  Superusuario, Directora, CEO, Contador, Auxiliar Contable

Uso (backend con venv y .env):
  venv\\Scripts\\python.exe scripts\\aplicar_estructura_usuarios.py

Idempotente: actualiza existentes y crea los que falten.
Escribe las claves temporales nuevas en:
  C:\\SuperOzono-Backups\\CREDENCIALES-ESTRUCTURA-USUARIOS-NO-SUBIR.txt
  (y Desktop\\Entrega-SuperOzono-v030\\ si existe)
"""
from __future__ import annotations

import secrets
import string
import sys
from pathlib import Path

# backend/ en path
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.core.tenancy import DEFAULT_TENANT_ID  # noqa: E402
from app.modules.usuarios.models import Usuario  # noqa: E402


def _temp_password(n: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    # garantiza letra + dígito (política)
    p = "".join(secrets.choice(alphabet) for _ in range(n - 2))
    p = p + secrets.choice(string.ascii_letters) + secrets.choice(string.digits)
    return p


# Plantilla de la empresa (ajustable)
DESIRED = [
    {
        "email": "admin@superozonoglobal.com",
        "nombre_completo": "Superusuario del Sistema",
        "rol": "Superusuario",
        "keep_password": True,  # no rotar la del superusuario
    },
    {
        "email": "directora@superozonoglobal.com",
        "nombre_completo": "Directora",
        "rol": "Directora",
        "aliases": ["administradora@superozonoglobal.com"],
    },
    {
        "email": "ceo@superozonoglobal.com",
        "nombre_completo": "CEO",
        "rol": "CEO",
    },
    {
        "email": "contador@superozonoglobal.com",
        "nombre_completo": "Contador",
        "rol": "Contador",
    },
    {
        "email": "auxiliar1@superozonoglobal.com",
        "nombre_completo": "Auxiliar Contable 1",
        "rol": "Auxiliar Contable",
        "aliases": ["auxiliar@superozonoglobal.com"],
    },
    {
        "email": "auxiliar2@superozonoglobal.com",
        "nombre_completo": "Auxiliar Contable 2",
        "rol": "Auxiliar Contable",
    },
    {
        "email": "auxiliar3@superozonoglobal.com",
        "nombre_completo": "Auxiliar Contable 3",
        "rol": "Auxiliar Contable",
    },
]


def _sync_url(async_url: str) -> str:
    return async_url.replace("sqlite+aiosqlite://", "sqlite://").replace(
        "postgresql+asyncpg://", "postgresql://"
    )


def main() -> None:
    settings = get_settings()
    engine = create_engine(_sync_url(settings.DATABASE_URL))
    creds_lines: list[str] = [
        "CREDENCIALES — estructura usuarios Super Ozono ERP",
        "URL: https://192.168.1.48:5173",
        "Cada usuario debe cambiar la contraseña al entrar.",
        "",
    ]

    with Session(engine) as session:
        # La migración Alembic b1c2d3e4f5a6 debe haber mapeado roles legacy.
        # No hacemos UPDATE de roles antiguos aquí: el CHECK de SQLite lo bloquearía.

        for spec in DESIRED:
            user = session.scalar(select(Usuario).where(Usuario.email == spec["email"]))
            if not user:
                for alias in spec.get("aliases", []):
                    user = session.scalar(select(Usuario).where(Usuario.email == alias))
                    if user:
                        user.email = spec["email"]
                        break

            if user:
                user.nombre_completo = spec["nombre_completo"]
                user.rol = spec["rol"]
                user.is_active = True
                if not getattr(user, "tenant_id", None):
                    user.tenant_id = DEFAULT_TENANT_ID
                temp = None
                if not spec.get("keep_password"):
                    temp = _temp_password()
                    user.hashed_password = get_password_hash(temp)
                session.flush()
                action = "actualizado"
            else:
                temp = _temp_password()
                user = Usuario(
                    email=spec["email"],
                    nombre_completo=spec["nombre_completo"],
                    rol=spec["rol"],
                    is_active=True,
                    hashed_password=get_password_hash(temp),
                    tenant_id=DEFAULT_TENANT_ID,
                )
                session.add(user)
                session.flush()
                action = "creado"

            if spec.get("keep_password"):
                creds_lines.append(
                    f"{spec['rol']}: {spec['email']}  (clave actual del Superusuario / SEED_ADMIN_PASSWORD)"
                )
            else:
                creds_lines.append(
                    f"{spec['rol']}: {spec['email']}  password_temporal: {temp}  [{action}]"
                )
            print(f"  {action}: {spec['email']} -> {spec['rol']}")

        session.commit()

    text_out = "\n".join(creds_lines) + "\n"
    out_paths = [
        Path(r"C:\SuperOzono-Backups\CREDENCIALES-ESTRUCTURA-USUARIOS-NO-SUBIR.txt"),
        Path.home() / "Desktop" / "Entrega-SuperOzono-v030" / "CREDENCIALES-ESTRUCTURA-USUARIOS.txt",
    ]
    for p in out_paths:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text_out, encoding="utf-8")
            print("escrito:", p)
        except OSError as e:
            print("no se pudo escribir", p, e)

    print("OK — reinicia el backend (stop/start) si ya estaba corriendo.")


if __name__ == "__main__":
    main()
