"""
Super Ozono Global — Schemas Pydantic para Auditoría
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RegistroAuditoriaResponse(BaseModel):
    id: int
    fecha: datetime
    usuario_id: Optional[int] = None
    usuario_email: Optional[str] = None
    accion: str
    entidad: str
    entidad_id: Optional[int] = None
    descripcion: str
    cambios: Optional[dict] = None  # {"campo": {"antes": ..., "despues": ...}}

    model_config = {"from_attributes": True}
