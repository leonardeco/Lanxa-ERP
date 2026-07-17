"""#24 — redondeo monetario configurable (half_even vs half_up)."""
import pytest
from decimal import Decimal

from app.core.money import redondear_cop

pytestmark = pytest.mark.no_db


def test_half_even_empate_va_al_par():
    # 1.225 → half_even a 2 decimales: 1.22 (2 es par)
    assert redondear_cop(Decimal("1.225"), "half_even") == Decimal("1.22")
    # 1.235 → 1.24 (3 impar → sube para dejar par)
    assert redondear_cop(Decimal("1.235"), "half_even") == Decimal("1.24")


def test_half_up_empate_sube():
    assert redondear_cop(Decimal("1.225"), "half_up") == Decimal("1.23")
    assert redondear_cop(Decimal("1.235"), "half_up") == Decimal("1.24")


def test_default_half_even():
    assert redondear_cop(Decimal("10.555")) == Decimal("10.56")
