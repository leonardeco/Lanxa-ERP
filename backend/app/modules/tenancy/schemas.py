from pydantic import BaseModel, EmailStr, Field


class TenantOnboardRequest(BaseModel):
    """Alta de una nueva empresa (tenant) con su Admin inicial."""

    codigo: str = Field(..., min_length=2, max_length=40, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    razon_social: str = Field(..., min_length=2, max_length=200)
    nit: str | None = Field(None, max_length=30)
    admin_email: EmailStr
    admin_nombre: str = Field(..., min_length=2, max_length=255)
    admin_password: str = Field(..., min_length=8, max_length=128)
    notas: str | None = None


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
