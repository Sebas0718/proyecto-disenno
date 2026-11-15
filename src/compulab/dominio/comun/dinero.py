"""Objeto de valor Dinero (colones).

Se usa ``Decimal`` y nunca ``float``: ``0.1 + 0.2`` en float da
``0.30000000000000004``, y en un cálculo de planilla eso termina en céntimos
de diferencia con lo que calcula Becas (ADR-0006).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from compulab.dominio.comun.errores import DatoInvalido

CENTIMOS = Decimal("0.01")


@dataclass(frozen=True, slots=True, order=True)
class Dinero:
    """Un monto en colones. Invariante: es un Decimal y no es negativo."""

    monto: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.monto, Decimal):
            raise DatoInvalido("Los montos se manejan con Decimal, nunca con float.")
        if not self.monto.is_finite() or self.monto < 0:
            raise DatoInvalido(f"Un monto no puede ser negativo ni infinito: {self.monto}.")

    @classmethod
    def cero(cls) -> Dinero:
        return cls(Decimal("0"))

    def __add__(self, otro: Dinero) -> Dinero:
        return Dinero(self.monto + otro.monto)

    def por(self, factor: Decimal) -> Dinero:
        """Multiplica el monto por un factor (horas, porcentaje de recargo...)."""
        return Dinero(self.monto * factor)

    def redondeado(self) -> Dinero:
        """Redondea a céntimos con la regla escolar (0,005 sube)."""
        return Dinero(self.monto.quantize(CENTIMOS, rounding=ROUND_HALF_UP))

    def __str__(self) -> str:
        return f"₡{self.redondeado().monto:,.2f}"
