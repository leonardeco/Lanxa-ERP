from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import TokenPayload

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login/access-token")

SessionDep = Annotated[AsyncSession, Depends(get_db)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(session: SessionDep, token: TokenDep) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await session.scalar(select(Usuario).where(Usuario.id == int(token_data.sub)))
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return user


# Alias base — cualquier usuario autenticado
CurrentUser = Annotated[Usuario, Depends(get_current_user)]


async def get_current_active_superuser(current_user: CurrentUser) -> Usuario:
    """Solo Admin."""
    if current_user.rol != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene suficientes privilegios",
        )
    return current_user


async def get_admin_or_administradora(current_user: CurrentUser) -> Usuario:
    """Admin o Administradora — operaciones sensibles (anular, abonar, maestros contables)."""
    if current_user.rol not in ("Admin", "Administradora"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para realizar esta operación",
        )
    return current_user


# Aliases de dependencia para usar en firmas de endpoints
AdminDep = Annotated[Usuario, Depends(get_current_active_superuser)]
AdminOrAdministradoraDep = Annotated[Usuario, Depends(get_admin_or_administradora)]
