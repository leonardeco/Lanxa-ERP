"""
Servicio de auditoría: registrar_auditoria() añade el evento a la sesión
(el commit/flush lo hace el endpoint que lo llama, dentro de su misma
transacción — si la operación falla, el registro también se revierte).
"""

import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auditoria.models import RegistroAuditoria

# Campos que jamás se escriben en el log (ni en claro ni hasheados)
_CAMPOS_SENSIBLES = {"password", "hashed_password"}


def _serializar(valor):
    """Valor apto para JSON, legible en la UI."""
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Enum):
        return valor.value
    return valor


def diff_cambios(obj, update_data: dict) -> dict:
    """Diff campo a campo entre el objeto actual y los datos del update.
    Solo incluye campos que realmente cambian; omite los sensibles."""
    cambios = {}
    for campo, nuevo in update_data.items():
        if campo in _CAMPOS_SENSIBLES:
            continue
        anterior = getattr(obj, campo, None)
        if _serializar(anterior) != _serializar(nuevo):
            cambios[campo] = {"antes": _serializar(anterior), "despues": _serializar(nuevo)}
    return cambios


def registrar_auditoria(
    db: AsyncSession,
    usuario,
    accion: str,
    entidad: str,
    entidad_id: int | None,
    descripcion: str,
    cambios: dict | None = None,
) -> None:
    """Añade el registro a la sesión (sin commit). Si `cambios` viene vacío
    (update sin cambios reales) igual se registra la acción, sin diff."""
    db.add(RegistroAuditoria(
        usuario_id=usuario.id if usuario else None,
        usuario_email=usuario.email if usuario else None,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        descripcion=descripcion[:300],
        cambios=json.dumps(cambios, ensure_ascii=False) if cambios else None,
    ))
