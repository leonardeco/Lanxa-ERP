from pydantic import BaseModel, EmailStr, field_validator

from app.core.passwords import PasswordPolicyError, validate_password_policy

# ── JWT Tokens ──


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str | None = None
    tenant_id: int | None = None

# ── Usuarios ──


class UsuarioBase(BaseModel):
    email: EmailStr
    nombre_completo: str
    rol: str = "Auxiliar"
    is_active: bool = True


def _pwd(v: str) -> str:
    try:
        return validate_password_policy(v)
    except PasswordPolicyError as exc:
        raise ValueError(str(exc)) from exc


class UsuarioCreate(UsuarioBase):
    password: str

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return _pwd(v)


class UsuarioUpdate(BaseModel):
    nombre_completo: str | None = None
    rol: str | None = None
    is_active: bool | None = None


class UsuarioPasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return _pwd(v)


class UsuarioPasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return _pwd(v)


class UsuarioResponse(UsuarioBase):
    id: int

    model_config = {"from_attributes": True}
