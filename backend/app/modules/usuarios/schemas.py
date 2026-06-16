from pydantic import BaseModel, EmailStr

# ── JWT Tokens ──
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: str | None = None

# ── Usuarios ──
class UsuarioBase(BaseModel):
    email: EmailStr
    nombre_completo: str
    rol: str = "Ventas"
    is_active: bool = True

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioResponse(UsuarioBase):
    id: int

    class Config:
        from_attributes = True
