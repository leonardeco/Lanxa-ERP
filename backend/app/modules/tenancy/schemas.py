from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.passwords import PasswordPolicyError, validate_password_policy


class TenantOnboardRequest(BaseModel):
    """Alta de una nueva empresa (tenant) con su Admin inicial."""

    codigo: str = Field(..., min_length=2, max_length=40, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    razon_social: str = Field(..., min_length=2, max_length=200)
    nit: str | None = Field(None, max_length=30)
    admin_email: EmailStr
    admin_nombre: str = Field(..., min_length=2, max_length=255)
    admin_password: str = Field(..., min_length=8, max_length=128)
    notas: str | None = None

    @field_validator("admin_password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        try:
            return validate_password_policy(v)
        except PasswordPolicyError as exc:
            raise ValueError(str(exc)) from exc


class TenantResponse(BaseModel):
    id: int
    codigo: str
    razon_social: str
    nit: str | None = None
    activo: bool

    model_config = {"from_attributes": True}


class TenantOnboardResponse(BaseModel):
    tenant: TenantResponse
    admin_email: str
    admin_id: int
    message: str
