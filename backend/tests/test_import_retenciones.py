"""Import CSV de flags de retención (#4) — unitario sin BD."""
import pytest

from app.modules.ventas.import_retenciones import (
    _map_headers,
    _parse_bool,
    _parse_tarifa,
    generar_plantilla_retenciones_csv,
)
from decimal import Decimal

pytestmark = pytest.mark.no_db


class _FakeCliente:
    def __init__(self, nit, razon, rf=False, ri=False, rc=False, tar=None, dv="1"):
        self.nit_cc = nit
        self.dv = dv
        self.razon_social = razon
        self.retiene_fuente = rf
        self.retiene_iva = ri
        self.retiene_ica = rc
        self.tarifa_reteica = tar


def test_parse_bool_si_no():
    assert _parse_bool("Sí") is True
    assert _parse_bool("no") is False
    assert _parse_bool("1") is True
    assert _parse_bool("") is None


def test_parse_tarifa():
    assert _parse_tarifa("4,140") == Decimal("4.140")
    assert _parse_tarifa("") is None
    assert isinstance(_parse_tarifa("xyz"), str)


def test_map_headers_export_ui():
    m = _map_headers(["NIT", "ReteFuente", "ReteIVA", "ReteICA", "Tarifa ReteICA ‰"])
    assert "nit" in m and "rf" in m and "ri" in m and "rc" in m


def test_plantilla_csv_bom_y_flags():
    csv_text = generar_plantilla_retenciones_csv([
        _FakeCliente("900111", "ACME", rf=True, tar=Decimal("4.14")),
    ])
    assert csv_text.startswith("\ufeff")
    assert "900111" in csv_text
    assert "Sí" in csv_text
    assert "retiene_fuente" in csv_text
