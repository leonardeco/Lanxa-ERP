from app.core.time import utcnow
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, func, select

from app.api.deps import SessionDep, CurrentUser, AdminDep
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.security import (
    verify_password, create_access_token, get_password_hash,
    generate_refresh_token, hash_refresh_token, refresh_token_expiry,
)
from app.modules.usuarios.models import Usuario, RefreshToken, ROLES_VALIDOS
from app.modules.usuarios.schemas import (
    Token, UsuarioCreate, UsuarioUpdate, UsuarioPasswordChange, UsuarioPasswordReset, UsuarioResponse,
)
from app.modules.auditoria.service import registrar_auditoria, diff_cambios

router = APIRouter()
settings = get_settings()

SuperuserDep = AdminDep

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/login"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=True,  # requiere HTTPS (certs/ generado por scripts/generate_tls_cert.py)
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )


# ── Auth ─────────────────────────────────────────────────

@router.post("/login/access-token", response_model=Token)
@limiter.limit("5/minute")
async def login_access_token(
    request: Request, response: Response, session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await session.scalar(select(Usuario).where(Usuario.email == form_data.username))
    # Mensaje único para credenciales malas Y usuario inactivo — evita enumerar
    # cuentas válidas o revelar su estado a un atacante (el Admin ve el estado
    # real en el módulo de Usuarios).
    if not user or not verify_password(form_data.password, user.hashed_password) or not user.is_active:
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")

    user_id = user.id  # capturado antes del commit: la sesion expira atributos al commitear

    # Limpieza oportunista: los refresh tokens vencidos no sirven para nada
    # y sin esto la tabla crece indefinidamente.
    await session.execute(delete(RefreshToken).where(RefreshToken.expires_at < utcnow()))

    raw_refresh = generate_refresh_token()
    session.add(RefreshToken(
        usuario_id=user_id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=refresh_token_expiry(),
    ))
    await session.commit()
    _set_refresh_cookie(response, raw_refresh)

    return Token(access_token=create_access_token(user_id), token_type="bearer")


@router.post("/login/refresh-token", response_model=Token)
async def refresh_access_token(request: Request, response: Response, session: SessionDep) -> Token:
    invalid = HTTPException(status_code=401, detail="Sesión expirada, inicie sesión de nuevo")

    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token:
        raise invalid

    stored = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if not stored or stored.expires_at < utcnow():
        response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
        raise invalid

    user = await session.scalar(select(Usuario).where(Usuario.id == stored.usuario_id))
    if not user or not user.is_active:
        await session.delete(stored)
        # commit ANTES del raise: si no, el rollback del manejador de la sesión
        # revierte el delete y el token del usuario inactivo queda vivo en BD
        await session.commit()
        raise invalid

    user_id = user.id  # capturado antes del commit: la sesion expira atributos al commitear

    # Rotación: el token usado se invalida y se emite uno nuevo
    await session.delete(stored)
    new_raw_refresh = generate_refresh_token()
    session.add(RefreshToken(
        usuario_id=user_id,
        token_hash=hash_refresh_token(new_raw_refresh),
        expires_at=refresh_token_expiry(),
    ))
    await session.commit()
    _set_refresh_cookie(response, new_raw_refresh)

    return Token(access_token=create_access_token(user_id), token_type="bearer")


@router.post("/login/logout")
async def logout(request: Request, response: Response, session: SessionDep) -> dict:
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        stored = await session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        )
        if stored:
            await session.delete(stored)
            await session.commit()
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    return {"detail": "Sesión cerrada"}


@router.get("/users/me", response_model=UsuarioResponse)
async def read_users_me(current_user: CurrentUser) -> UsuarioResponse:
    return UsuarioResponse.model_validate(current_user)


async def _es_ultimo_admin_activo(session, user: Usuario) -> bool:
    """True si `user` es Admin activo y no queda ningún otro Admin activo."""
    if user.rol != "Admin" or not user.is_active:
        return False
    otros = await session.scalar(
        select(func.count(Usuario.id)).where(
            Usuario.rol == "Admin",
            Usuario.is_active.is_(True),
            Usuario.id != user.id,
        )
    )
    return (otros or 0) == 0


# ── CRUD Usuarios (solo Superadmin) ──────────────────────

@router.get("/v1/usuarios", response_model=List[UsuarioResponse])
async def list_usuarios(session: SessionDep, _: SuperuserDep):
    result = await session.execute(select(Usuario).order_by(Usuario.nombre_completo))
    return result.scalars().all()


@router.post("/v1/usuarios", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def create_usuario(body: UsuarioCreate, session: SessionDep, admin: SuperuserDep):
    if body.rol not in ROLES_VALIDOS:
        raise HTTPException(400, f"Rol inválido. Opciones: {', '.join(sorted(ROLES_VALIDOS))}")
    existing = await session.scalar(select(Usuario).where(Usuario.email == body.email))
    if existing:
        raise HTTPException(400, "Ya existe un usuario con ese correo")
    user = Usuario(
        email=body.email,
        nombre_completo=body.nombre_completo,
        rol=body.rol,
        is_active=body.is_active,
        hashed_password=get_password_hash(body.password),
    )
    session.add(user)
    await session.flush()
    registrar_auditoria(session, admin, "Crear", "Usuario", user.id,
                        f"Usuario {user.email} (rol {user.rol})")
    await session.commit()
    await session.refresh(user)
    return user


@router.put("/v1/usuarios/{user_id}", response_model=UsuarioResponse)
async def update_usuario(user_id: int, body: UsuarioUpdate, session: SessionDep, admin: SuperuserDep):
    user = await session.get(Usuario, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if body.rol is not None and body.rol not in ROLES_VALIDOS:
        raise HTTPException(400, f"Rol inválido. Opciones: {', '.join(sorted(ROLES_VALIDOS))}")
    # Guard de último admin: no permitir dejar el sistema sin ningún Admin activo
    pierde_admin = (body.rol is not None and body.rol != "Admin") or body.is_active is False
    if pierde_admin and await _es_ultimo_admin_activo(session, user):
        raise HTTPException(400, "No se puede quitar el rol o desactivar al último Admin activo del sistema")
    cambios = diff_cambios(user, body.model_dump(exclude_none=True))
    if body.nombre_completo is not None:
        user.nombre_completo = body.nombre_completo
    if body.rol is not None:
        user.rol = body.rol
    if body.is_active is not None:
        user.is_active = body.is_active
    if cambios:
        registrar_auditoria(session, admin, "Actualizar", "Usuario", user.id,
                            f"Usuario {user.email}", cambios)
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/v1/usuarios/{user_id}/toggle", response_model=UsuarioResponse)
async def toggle_usuario(user_id: int, session: SessionDep, current_user: CurrentUser, _: SuperuserDep):
    user = await session.get(Usuario, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(400, "No puedes desactivarte a ti mismo")
    if user.is_active and await _es_ultimo_admin_activo(session, user):
        raise HTTPException(400, "No se puede desactivar al último Admin activo del sistema")
    user.is_active = not user.is_active
    registrar_auditoria(session, current_user, "Activar" if user.is_active else "Desactivar",
                        "Usuario", user.id, f"Usuario {user.email}")
    await session.commit()
    await session.refresh(user)
    return user


@router.put("/v1/usuarios/{user_id}/reset-password")
@limiter.limit("5/minute")
async def reset_usuario_password(
    request: Request, user_id: int, body: UsuarioPasswordReset, session: SessionDep, admin: SuperuserDep
):
    """Resetea la contraseña de un usuario sin acceso. Solo Admin."""
    user = await session.get(Usuario, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if len(body.new_password) < 8:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 8 caracteres")
    user.hashed_password = get_password_hash(body.new_password)
    # Se registra el hecho, nunca la contraseña
    registrar_auditoria(session, admin, "Resetear contraseña", "Usuario", user.id,
                        f"Usuario {user.email}")
    await session.commit()
    return {"message": "Contraseña restablecida correctamente"}


@router.post("/v1/usuarios/{user_id}/revocar-sesiones")
async def revocar_sesiones_usuario(user_id: int, session: SessionDep, admin: SuperuserDep):
    """Cierra las sesiones remotas de un usuario borrando sus refresh tokens.
    El access token vigente expira solo (máx. 15 min); sin refresh token no
    puede renovarse, así que la sesión muere sin necesidad de desactivarlo."""
    user = await session.get(Usuario, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    result = await session.execute(
        delete(RefreshToken).where(RefreshToken.usuario_id == user_id)
    )
    revocadas = getattr(result, "rowcount", 0) or 0
    registrar_auditoria(session, admin, "Revocar sesiones", "Usuario", user.id,
                        f"Usuario {user.email} — {revocadas} sesión(es) revocada(s)")
    await session.commit()
    return {"message": f"{revocadas} sesión(es) revocada(s) para {user.email}",
            "sesiones_revocadas": revocadas}


# ── Cambio de contraseña propia (cualquier usuario) ──────

@router.put("/v1/usuarios/me/password")
@limiter.limit("10/minute")
async def change_my_password(
    request: Request, body: UsuarioPasswordChange, session: SessionDep, current_user: CurrentUser
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(400, "Contraseña actual incorrecta")
    if len(body.new_password) < 8:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 8 caracteres")
    current_user.hashed_password = get_password_hash(body.new_password)
    await session.commit()
    return {"message": "Contraseña actualizada correctamente"}
