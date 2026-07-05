"""
Super Ozono Global — API de consulta del log de auditoría (solo lectura).
Los registros se crean desde los endpoints instrumentados vía service.py.
"""

import json
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import AdminOrAdministradoraDep
from app.modules.auditoria.models import RegistroAuditoria
from app.modules.auditoria.schemas import RegistroAuditoriaResponse

router = APIRouter(prefix="/api/v1/auditoria", tags=["Auditoría"])


@router.get("", response_model=List[RegistroAuditoriaResponse])
async def list_auditoria(
    _: AdminOrAdministradoraDep,
    entidad: Optional[str] = Query(None, description="Filtrar por entidad (Producto, Cliente...)"),
    accion: Optional[str] = Query(None),
    usuario_id: Optional[int] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Listar el log de auditoría (más recientes primero)."""
    q = (
        select(RegistroAuditoria)
        .order_by(desc(RegistroAuditoria.fecha), desc(RegistroAuditoria.id))
        .limit(limit)
        .offset(offset)
    )
    if entidad:
        q = q.where(RegistroAuditoria.entidad == entidad)
    if accion:
        q = q.where(RegistroAuditoria.accion == accion)
    if usuario_id:
        q = q.where(RegistroAuditoria.usuario_id == usuario_id)
    if fecha_desde:
        q = q.where(RegistroAuditoria.fecha >= fecha_desde)
    if fecha_hasta:
        # inclusive: hasta el final del día indicado
        q = q.where(RegistroAuditoria.fecha < fecha_hasta + timedelta(days=1))

    rows = (await db.execute(q)).scalars().all()
    return [
        RegistroAuditoriaResponse(
            id=r.id,
            fecha=r.fecha,
            usuario_id=r.usuario_id,
            usuario_email=r.usuario_email,
            accion=r.accion,
            entidad=r.entidad,
            entidad_id=r.entidad_id,
            descripcion=r.descripcion,
            cambios=json.loads(r.cambios) if r.cambios else None,
        )
        for r in rows
    ]
