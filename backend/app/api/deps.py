from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.tenancy import DEFAULT_TENANT_ID, apply_rls_tenant, set_tenant_id
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
        user_id = int(token_data.sub)
    except (PyJWTError, ValueError):
        # PyJWTError: token inválido, malformado, con firma incorrecta o expirado.
        # ValueError: sub no numérico en un token firmado con otra estructura —
        # debe ser 401, no un 500 por int() fallido
        raise credentials_exception

    user = await session.scalar(select(Usuario).where(Usuario.id == user_id))
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    # Run 2/3: fijar tenant del request (claim JWT o columna del usuario; fallback LAN)
    # y alinear la GUC de RLS en la misma sesión.
    tid = token_data.tenant_id
    if tid is None:
        tid = getattr(user, "tenant_id", None) or DEFAULT_TENANT_ID
    if getattr(user, "tenant_id", None) is not None and tid != user.tenant_id:
        # No permitir escalar a otro tenant con un JWT manipulado.
        raise credentials_exception
    set_tenant_id(int(tid))
    await apply_rls_tenant(session, int(tid))
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
    """Admin o Administradora — operaciones sensibles (anular ventas/compras, etc.)."""
    if current_user.rol not in ("Admin", "Administradora"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para realizar esta operación",
        )
    return current_user


async def get_area_contable(current_user: CurrentUser) -> Usuario:
    """Admin, Administradora o Contador — área contable: maestros contables (PUC,
    centros de costo, períodos, tributarios), cartera y sus abonos/anulaciones.
    El Contador NO puede gestionar usuarios ni anular ventas/compras."""
    if current_user.rol not in ("Admin", "Administradora", "Contador"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para realizar esta operación",
        )
    return current_user


# Aliases de dependencia para usar en firmas de endpoints
AdminDep = Annotated[Usuario, Depends(get_current_active_superuser)]
AdminOrAdministradoraDep = Annotated[Usuario, Depends(get_admin_or_administradora)]
ContableDep = Annotated[Usuario, Depends(get_area_contable)]
