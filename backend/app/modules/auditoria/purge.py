"""
Archivado y purga del log de auditoría (#28).

Exporta a un archivo JSON cifrado los registros anteriores al corte de
retención, verifica el archivo, y solo entonces los borra — dejando el propio
evento de purga registrado en la auditoría. Usado por scripts/purge_auditoria.py
(manual o Programador de tareas).

Idempotente/seguro ante fallo parcial: la escritura del archivo y el DELETE no
son una sola transacción; si el commit falla tras escribir el archivo, las filas
quedan y una nueva corrida las re-archiva y borra. El borrado nunca ocurre sin un
archivo verificado.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.modules.auditoria.models import RegistroAuditoria
from app.modules.auditoria.service import registrar_auditoria


@dataclass
class ResultadoPurga:
    registros: int
    archivo: Path | None
    corte: datetime


def _registro_a_dict(r: RegistroAuditoria) -> dict:
    return {
        "id": r.id,
        "fecha": r.fecha.isoformat() if r.fecha else None,
        "usuario_id": r.usuario_id,
        "usuario_email": r.usuario_email,
        "accion": r.accion,
        "entidad": r.entidad,
        "entidad_id": r.entidad_id,
        "descripcion": r.descripcion,
        "cambios": json.loads(r.cambios) if r.cambios else None,
        "ip": r.ip,
    }


async def purgar_auditoria(
    db: AsyncSession,
    corte: datetime,
    archive_dir: Path,
    encryption_key: str,
) -> ResultadoPurga:
    """Archiva (cifrado) y borra los registros de auditoría con fecha < corte.

    Si no hay registros, no crea archivo y devuelve registros=0. Lanza
    ValueError si falta la clave de cifrado cuando sí hay algo que archivar.
    """
    rows = (
        await db.execute(
            select(RegistroAuditoria)
            .where(RegistroAuditoria.fecha < corte)
            .order_by(RegistroAuditoria.fecha, RegistroAuditoria.id)
        )
    ).scalars().all()

    if not rows:
        return ResultadoPurga(registros=0, archivo=None, corte=corte)

    if not encryption_key:
        raise ValueError(
            "Se requiere BACKUP_ENCRYPTION_KEY para cifrar el archivo de "
            "auditoría antes de purgar; abortando sin borrar nada."
        )

    datos = [_registro_a_dict(r) for r in rows]
    payload = json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8")

    fernet = Fernet(encryption_key.encode())
    cifrado = fernet.encrypt(payload)

    archive_dir.mkdir(parents=True, exist_ok=True)
    ts = utcnow().strftime("%Y-%m-%d_%H%M%S")
    destino = archive_dir / f"auditoria_purga_{ts}.json.enc"
    destino.write_bytes(cifrado)

    # Verificar el archivo antes de borrar: descifrar y contar.
    verificado = json.loads(fernet.decrypt(destino.read_bytes()).decode("utf-8"))
    if len(verificado) != len(rows):
        raise RuntimeError(
            f"Verificacion del archivo fallo: esperados {len(rows)}, "
            f"el archivo tiene {len(verificado)}. No se borro nada."
        )

    await db.execute(
        delete(RegistroAuditoria).where(RegistroAuditoria.fecha < corte)
    )

    registrar_auditoria(
        db,
        usuario=None,
        accion="Purgar",
        entidad="Auditoria",
        entidad_id=None,
        descripcion=(
            f"Archivados y purgados {len(rows)} registros con fecha < "
            f"{corte.isoformat()} -> {destino.name}"
        ),
    )
    await db.commit()

    return ResultadoPurga(registros=len(rows), archivo=destino, corte=corte)
