from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy import select

from app.api.deps import SessionDep, CurrentUser, AdminDep
from app.core.security import verify_password, create_access_token, get_password_hash
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    Token, UsuarioCreate, UsuarioUpdate, UsuarioPasswordChange, UsuarioResponse,
)

router = APIRouter()

SuperuserDep = AdminDep

ROLES_VALIDOS = {"Admin", "Administradora", "Auxiliar"}


# ── Auth ─────────────────────────────────────────────────

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    user = await session.scalar(select(Usuario).where(Usuario.email == form_data.username))
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return Token(access_token=create_access_token(user.id), token_type="bearer")


@router.get("/users/me", response_model=UsuarioResponse)
async def read_users_me(current_user: CurrentUser) -> UsuarioResponse:
    return current_user


# ── CRUD Usuarios (solo Superadmin) ──────────────────────

@router.get("/v1/usuarios", response_model=List[UsuarioResponse])
async def list_usuarios(session: SessionDep, _: SuperuserDep):
    result = await session.execute(select(Usuario).order_by(Usuario.nombre_completo))
    return result.scalars().all()


@router.post("/v1/usuarios", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def create_usuario(body: UsuarioCreate, session: SessionDep, _: SuperuserDep):
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
    await session.commit()
    await session.refresh(user)
    return user


@router.put("/v1/usuarios/{user_id}", response_model=UsuarioResponse)
async def update_usuario(user_id: int, body: UsuarioUpdate, session: SessionDep, _: SuperuserDep):
    user = await session.get(Usuario, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    if body.rol is not None and body.rol not in ROLES_VALIDOS:
        raise HTTPException(400, f"Rol inválido. Opciones: {', '.join(sorted(ROLES_VALIDOS))}")
    if body.nombre_completo is not None:
        user.nombre_completo = body.nombre_completo
    if body.rol is not None:
        user.rol = body.rol
    if body.is_active is not None:
        user.is_active = body.is_active
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
    user.is_active = not user.is_active
    await session.commit()
    await session.refresh(user)
    return user


# ── Cambio de contraseña propia (cualquier usuario) ──────

@router.put("/v1/usuarios/me/password")
async def change_my_password(body: UsuarioPasswordChange, session: SessionDep, current_user: CurrentUser):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(400, "Contraseña actual incorrecta")
    if len(body.new_password) < 8:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 8 caracteres")
    current_user.hashed_password = get_password_hash(body.new_password)
    await session.commit()
    return {"message": "Contraseña actualizada correctamente"}
