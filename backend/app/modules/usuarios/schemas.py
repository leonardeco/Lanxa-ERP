from pydantic import BaseModel, EmailStr

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


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioUpdate(BaseModel):
    nombre_completo: str | None = None
    rol: str | None = None
    is_active: bool | None = None


class UsuarioPasswordChange(BaseModel):
    current_password: str
    new_password: str


class UsuarioPasswordReset(BaseModel):
    new_password: str


class UsuarioResponse(UsuarioBase):
    id: int

    model_config = {"from_attributes": True}
