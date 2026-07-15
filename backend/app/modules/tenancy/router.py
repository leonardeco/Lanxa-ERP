"""
Onboarding multi-empresa (Run 5).

Solo un Admin del tenant plataforma (DEFAULT_TENANT_ID = Super Ozono) puede
crear nuevas empresas. Cada empresa nace con su propio Admin.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AdminDep
from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.tenancy import (
    DEFAULT_TENANT_ID,
    Tenant,
    apply_rls_tenant,
    get_tenant_id,
    set_tenant_id,
)
from app.modules.tenancy.schemas import (
    TenantOnboardRequest,
    TenantOnboardResponse,
    TenantResponse,
)
from app.modules.usuarios.models import Usuario
from app.modules.auditoria.service import registrar_auditoria

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenants / Multi-empresa"])


def _require_platform_admin(admin: Usuario) -> None:
    """Solo operadores del tenant #1 (plataforma) crean empresas nuevas."""
    tid = getattr(admin, "tenant_id", None) or get_tenant_id()
    if int(tid) != DEFAULT_TENANT_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el Admin de la plataforma (tenant Super Ozono) puede dar de alta empresas",
        )


@router.get("/", response_model=list[TenantResponse])
async def list_tenants(
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """Lista empresas. Plataforma ve todas; otros tenants solo la propia."""
    _ = admin
    tid = get_tenant_id()
    if tid == DEFAULT_TENANT_ID:
        rows = (await db.execute(select(Tenant).order_by(Tenant.id))).scalars().all()
    else:
        rows = (
            await db.execute(select(Tenant).where(Tenant.id == tid))
        ).scalars().all()
    return rows


@router.post("/onboard", response_model=TenantOnboardResponse, status_code=201)
async def onboard_tenant(
    body: TenantOnboardRequest,
    admin: AdminDep,
    db: AsyncSession = Depends(get_db),
):
    """
    Crea un tenant nuevo + usuario Admin inicial.

    El request debe ir autenticado como Admin del tenant plataforma (id=1).
    Tras crear, el GUC/context se restaura al tenant plataforma.
    """
    _require_platform_admin(admin)

    codigo = body.codigo.strip().lower()
    existing = await db.scalar(select(Tenant).where(Tenant.codigo == codigo))
    if existing:
        raise HTTPException(400, f"Ya existe un tenant con código '{codigo}'")

    # tenants no tiene RLS; inserts de filas tenant-scoped requieren GUC del NUEVO tenant
    tenant = Tenant(
        codigo=codigo,
        razon_social=body.razon_social.strip(),
        nit=body.nit,
        activo=True,
        notas=body.notas,
    )
    db.add(tenant)
    await db.flush()

    # Cambiar contexto al nuevo tenant para stamp + RLS del Admin
    prev = get_tenant_id()
    set_tenant_id(tenant.id)
    await apply_rls_tenant(db, tenant.id)
    try:
        email_taken = await db.scalar(
            select(Usuario.id).where(
                Usuario.email == str(body.admin_email),
                Usuario.tenant_id == tenant.id,
            )
        )
        if email_taken:
            raise HTTPException(400, "Ya existe ese email en el nuevo tenant")

        user = Usuario(
            email=str(body.admin_email).lower(),
            nombre_completo=body.admin_nombre.strip(),
            rol="Superusuario",
            is_active=True,
            hashed_password=get_password_hash(body.admin_password),
            tenant_id=tenant.id,
        )
        db.add(user)
        await db.flush()
        registrar_auditoria(
            db,
            admin,
            "Crear",
            "Tenant",
            tenant.id,
            f"Onboard tenant {tenant.codigo} admin={user.email}",
        )
        await db.flush()
        admin_id = user.id
        admin_email = user.email
    finally:
        set_tenant_id(prev)
        await apply_rls_tenant(db, prev)

    return TenantOnboardResponse(
        tenant=TenantResponse.model_validate(tenant),
        admin_email=admin_email,
        admin_id=admin_id,
        message=(
            f"Empresa '{tenant.razon_social}' creada (id={tenant.id}). "
            f"Admin inicial: {admin_email}. Debe cambiar la contraseña en el primer login."
        ),
    )
