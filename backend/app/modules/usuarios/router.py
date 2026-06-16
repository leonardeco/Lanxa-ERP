from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import SessionDep, CurrentUser
from app.core.security import verify_password, create_access_token
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import Token, UsuarioResponse

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """OAuth2 compatible token login, get an access token for future requests"""
    user = await session.scalar(select(Usuario).where(Usuario.email == form_data.username))
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Correo o contraseña incorrectos")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
        
    access_token = create_access_token(user.id)
    return Token(access_token=access_token, token_type="bearer")

@router.get("/users/me", response_model=UsuarioResponse)
async def read_users_me(current_user: CurrentUser) -> UsuarioResponse:
    """Obtener los detalles del usuario actualmente logueado."""
    return current_user
