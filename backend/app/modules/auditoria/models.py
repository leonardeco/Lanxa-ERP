"""
Super Ozono Global — Auditoría de cambios (audit log)
Quién modificó qué en los datos maestros (productos, clientes, proveedores,
parámetros) y acciones administrativas (usuarios, períodos).
"""

from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.time import utcnow


class RegistroAuditoria(Base):
    """Un evento de auditoría. `cambios` guarda el diff campo a campo como
    JSON: {"campo": {"antes": ..., "despues": ...}} — solo en actualizaciones."""
    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    # Snapshot del email: el registro sigue siendo legible si el usuario cambia
    usuario_email: Mapped[str | None] = mapped_column(String(150))
    accion: Mapped[str] = mapped_column(String(30), index=True)   # Crear/Actualizar/Desactivar/...
    entidad: Mapped[str] = mapped_column(String(50), index=True)  # Producto, Cliente, ...
    entidad_id: Mapped[int | None] = mapped_column()
    descripcion: Mapped[str] = mapped_column(String(300))         # "Producto SOZ-001 — Biocida 1L"
    cambios: Mapped[str | None] = mapped_column(Text)             # JSON del diff (solo updates)
    ip: Mapped[str | None] = mapped_column(String(45))            # IP del request (IPv4/IPv6)

    usuario = relationship("Usuario")

    def __repr__(self):
        return f"<RegistroAuditoria {self.accion} {self.entidad}#{self.entidad_id}>"
