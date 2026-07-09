"""
Archiva (cifrado) y purga los registros de auditoría anteriores al periodo de
retención (#28). Espejo operativo de scripts/backup_db.py — pensado para el
Programador de tareas de Windows.

Uso: venv\\Scripts\\python.exe scripts\\purge_auditoria.py
"""
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings          # noqa: E402
from app.core.database import async_session        # noqa: E402
from app.core.time import utcnow                    # noqa: E402

# Registrar todos los modelos en el mapper registry — igual que alembic/env.py.
# Sin esto, la relación RegistroAuditoria→Usuario no resuelve al consultar desde
# un proceso standalone (la app y los tests ya importan estos módulos).
from app.modules.usuarios import models as _usuarios_models          # noqa: E402,F401
from app.modules.contabilidad import models as _contabilidad_models  # noqa: E402,F401
from app.modules.ventas import models as _ventas_models              # noqa: E402,F401
from app.modules.compras import models as _compras_models            # noqa: E402,F401
from app.modules.inventario import models as _inventario_models      # noqa: E402,F401

from app.modules.auditoria.purge import purgar_auditoria  # noqa: E402


async def _run() -> None:
    settings = get_settings()
    corte = utcnow() - timedelta(days=settings.AUDITORIA_RETENTION_DAYS)
    archive_dir = Path(settings.BACKUP_DIR) / "auditoria"

    async with async_session() as db:
        resultado = await purgar_auditoria(
            db, corte, archive_dir, settings.BACKUP_ENCRYPTION_KEY
        )

    if resultado.registros == 0:
        print(
            f"Nada que purgar (retencion {settings.AUDITORIA_RETENTION_DAYS} "
            f"dias, corte {corte.date()})."
        )
    else:
        print(f"Purgados {resultado.registros} registros -> {resultado.archivo}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
