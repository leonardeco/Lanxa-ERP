"""
Purga/archivado del log de auditoría (#28): archiva cifrado y borra los
registros anteriores al corte de retención, deja el evento auditado.
"""
import json
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select, func

from app.core.time import utcnow
from app.modules.auditoria.models import RegistroAuditoria
from app.modules.auditoria.purge import purgar_auditoria

RETENCION = 1825


def _make_registro(dias_atras: int, accion="Crear", entidad="Producto"):
    return RegistroAuditoria(
        fecha=utcnow() - timedelta(days=dias_atras),
        usuario_id=None,
        usuario_email="viejo@test.com",
        accion=accion,
        entidad=entidad,
        entidad_id=1,
        descripcion=f"registro de hace {dias_atras} dias",
        cambios=json.dumps({"precio": {"antes": "1", "despues": "2"}}),
        ip="127.0.0.1",
    )


@pytest.mark.asyncio
async def test_purga_borra_viejos_conserva_recientes(db_session, tmp_path):
    key = Fernet.generate_key().decode()
    db_session.add(_make_registro(2000))
    db_session.add(_make_registro(1900))
    db_session.add(_make_registro(10))
    await db_session.commit()

    corte = utcnow() - timedelta(days=RETENCION)
    resultado = await purgar_auditoria(db_session, corte, tmp_path, key)

    assert resultado.registros == 2
    assert resultado.archivo is not None and resultado.archivo.exists()

    restantes = (await db_session.execute(select(RegistroAuditoria))).scalars().all()
    assert sum(1 for r in restantes if r.accion == "Crear") == 1
    purga = next(r for r in restantes if r.accion == "Purgar")
    assert purga.entidad == "Auditoria"
    assert "2 registros" in purga.descripcion


@pytest.mark.asyncio
async def test_archivo_cifrado_descifra_a_los_registros(db_session, tmp_path):
    key = Fernet.generate_key().decode()
    db_session.add(_make_registro(2000))
    await db_session.commit()

    corte = utcnow() - timedelta(days=RETENCION)
    resultado = await purgar_auditoria(db_session, corte, tmp_path, key)

    contenido = Fernet(key.encode()).decrypt(resultado.archivo.read_bytes())
    datos = json.loads(contenido)
    assert len(datos) == 1
    assert datos[0]["usuario_email"] == "viejo@test.com"
    assert datos[0]["cambios"]["precio"]["despues"] == "2"


@pytest.mark.asyncio
async def test_sin_registros_no_crea_archivo(db_session, tmp_path):
    db_session.add(_make_registro(10))
    await db_session.commit()

    corte = utcnow() - timedelta(days=RETENCION)
    resultado = await purgar_auditoria(db_session, corte, tmp_path, encryption_key="")

    assert resultado.registros == 0
    assert resultado.archivo is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_falta_clave_aborta_sin_borrar(db_session, tmp_path):
    db_session.add(_make_registro(2000))
    await db_session.commit()

    corte = utcnow() - timedelta(days=RETENCION)
    with pytest.raises(ValueError):
        await purgar_auditoria(db_session, corte, tmp_path, encryption_key="")

    total = (await db_session.execute(
        select(func.count()).select_from(RegistroAuditoria))).scalar()
    assert total == 1
