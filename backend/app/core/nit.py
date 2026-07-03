"""
Dígito de verificación del NIT — algoritmo oficial DIAN (Orden 4144 de 1989).

Los pesos se aplican a los dígitos del NIT de derecha a izquierda; la suma
módulo 11 produce el DV (si el residuo es 0 o 1, el DV es el residuo).
"""

_PESOS = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


def calcular_dv(nit: str) -> int | None:
    """DV del NIT, o None si el NIT no es numérico (cédulas extranjería, etc.)."""
    nit = nit.strip().replace(".", "").replace("-", "")
    if not nit.isdigit() or len(nit) > len(_PESOS):
        return None
    suma = sum(int(d) * p for d, p in zip(reversed(nit), _PESOS))
    residuo = suma % 11
    return residuo if residuo < 2 else 11 - residuo


def validar_dv(nit: str, dv: str | None) -> str | None:
    """
    Si se suministró un DV y el NIT es numérico, verifica que coincida con el
    calculado. Devuelve un mensaje de error o None si es válido/no aplica.
    """
    if not dv:
        return None
    esperado = calcular_dv(nit)
    if esperado is None:
        return None  # NIT no numérico: no se puede validar, se acepta
    if str(esperado) != dv.strip():
        return (
            f"El dígito de verificación no coincide: para el NIT {nit} "
            f"el DV correcto es {esperado}, no {dv}"
        )
    return None
