"""
Importación de flags de retención en clientes (#4 helper).

CSV con separador ';' (mismo estilo que exportCsv del frontend).
Columnas mínimas: nit_cc + retiene_fuente + retiene_iva + retiene_ica
Opcional: tarifa_reteica (por mil).

No inventa quién retiene: solo aplica lo que el Contador/empresa escribe
en el archivo (p. ej. tras exportar, editar en Excel y reimportar).
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenancy import tenant_clause
from app.modules.ventas.models import Cliente
from app.modules.auditoria.service import registrar_auditoria

# Encabezados aceptados (minúsculas, sin tildes en aliases)
_ALIASES_NIT = frozenset({"nit", "nit_cc", "nit / cc", "nit_cc"})
_ALIASES_RF = frozenset({"retefuente", "retiene_fuente", "rtef"})
_ALIASES_RI = frozenset({"reteiva", "retiene_iva", "rteiva"})
_ALIASES_RC = frozenset({"reteica", "retiene_ica", "rteica"})
_ALIASES_TAR = frozenset({"tarifa_reteica", "tarifa reteica ‰", "tarifa reteica", "tarifa_reteica_pm"})


def _norm_header(h: str) -> str:
    return (h or "").strip().lower().replace("í", "i").replace("ó", "o")


def _parse_bool(v: str | None) -> bool | None:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("", "-"):
        return None
    if s in ("1", "si", "sí", "s", "true", "yes", "y", "x"):
        return True
    if s in ("0", "no", "n", "false"):
        return False
    return None


def _parse_tarifa(v: str | None) -> Decimal | None | str:
    """Decimal, None si vacío, o str de error."""
    if v is None or str(v).strip() == "":
        return None
    s = str(v).strip().replace(",", ".")
    try:
        d = Decimal(s)
    except InvalidOperation:
        return f"tarifa inválida: {v!r}"
    if d < 0 or d > 100:
        return f"tarifa fuera de rango (0–100): {d}"
    return d


@dataclass
class ResultadoImportRetenciones:
    actualizados: int = 0
    sin_cambio: int = 0
    no_encontrados: list[str] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    filas_leidas: int = 0


def _map_headers(fieldnames: list[str] | None) -> dict[str, str]:
    """Mapa rol -> nombre original de columna."""
    mapping: dict[str, str] = {}
    for raw in fieldnames or []:
        n = _norm_header(raw)
        if n in _ALIASES_NIT or n.startswith("nit"):
            mapping.setdefault("nit", raw)
        elif n in _ALIASES_RF:
            mapping.setdefault("rf", raw)
        elif n in _ALIASES_RI:
            mapping.setdefault("ri", raw)
        elif n in _ALIASES_RC:
            mapping.setdefault("rc", raw)
        elif n in _ALIASES_TAR or "tarifa" in n and "ica" in n:
            mapping.setdefault("tar", raw)
    return mapping


async def importar_retenciones_csv(
    db: AsyncSession,
    contenido: bytes | str,
    usuario,
) -> ResultadoImportRetenciones:
    """Aplica flags de retención desde CSV. Solo actualiza clientes existentes del tenant."""
    out = ResultadoImportRetenciones()
    if isinstance(contenido, bytes):
        text = contenido.decode("utf-8-sig")
    else:
        text = contenido

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        out.errores.append("CSV vacío o sin encabezados")
        return out

    cols = _map_headers(list(reader.fieldnames))
    if "nit" not in cols:
        out.errores.append(
            "Falta columna de NIT (nit_cc / NIT). Use el CSV exportado desde Clientes."
        )
        return out
    if not any(k in cols for k in ("rf", "ri", "rc")):
        out.errores.append(
            "Falta al menos una columna de retención (ReteFuente / ReteIVA / ReteICA)"
        )
        return out

    for i, row in enumerate(reader, start=2):
        out.filas_leidas += 1
        nit = (row.get(cols["nit"]) or "").strip()
        if not nit:
            out.errores.append(f"Fila {i}: NIT vacío")
            continue

        # Quitar DV si vino como 900123456-7
        if "-" in nit and nit.rsplit("-", 1)[-1].isdigit() and len(nit.rsplit("-", 1)[-1]) == 1:
            nit = nit.rsplit("-", 1)[0].strip()

        cliente = await db.scalar(
            select(Cliente).where(Cliente.nit_cc == nit, tenant_clause(Cliente))
        )
        if not cliente:
            out.no_encontrados.append(nit)
            continue

        cambios: dict = {}
        if "rf" in cols:
            b = _parse_bool(row.get(cols["rf"]))
            if b is not None and b != cliente.retiene_fuente:
                cambios["retiene_fuente"] = b
        if "ri" in cols:
            b = _parse_bool(row.get(cols["ri"]))
            if b is not None and b != cliente.retiene_iva:
                cambios["retiene_iva"] = b
        if "rc" in cols:
            b = _parse_bool(row.get(cols["rc"]))
            if b is not None and b != cliente.retiene_ica:
                cambios["retiene_ica"] = b
        if "tar" in cols:
            t = _parse_tarifa(row.get(cols["tar"]))
            if isinstance(t, str):
                out.errores.append(f"Fila {i} ({nit}): {t}")
                continue
            if t is not None and t != cliente.tarifa_reteica:
                cambios["tarifa_reteica"] = t
            elif t is None and cliente.tarifa_reteica is not None and row.get(cols["tar"], "").strip() == "":
                # no borrar tarifa si celda vacía
                pass

        if not cambios:
            out.sin_cambio += 1
            continue

        for k, v in cambios.items():
            setattr(cliente, k, v)
        registrar_auditoria(
            db,
            usuario,
            "Actualizar",
            "Cliente",
            cliente.id,
            f"Import retenciones NIT {nit}: {', '.join(f'{k}={v}' for k, v in cambios.items())}",
            cambios={k: {"antes": None, "despues": str(v)} for k, v in cambios.items()},
        )
        out.actualizados += 1

    await db.flush()
    return out


def generar_plantilla_retenciones_csv(clientes: list[Cliente]) -> str:
    """CSV listo para editar en Excel (es-CO) y reimportar."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow([
        "nit_cc", "dv", "razon_social",
        "retiene_fuente", "retiene_iva", "retiene_ica", "tarifa_reteica",
    ])
    for c in clientes:
        w.writerow([
            c.nit_cc,
            c.dv or "",
            c.razon_social,
            "Sí" if c.retiene_fuente else "No",
            "Sí" if c.retiene_iva else "No",
            "Sí" if c.retiene_ica else "No",
            str(c.tarifa_reteica) if c.tarifa_reteica is not None else "",
        ])
    return "\ufeff" + buf.getvalue()
