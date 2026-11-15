"""Tarifario: tarifas por categoría y porcentaje de recargo, con vigencia.

"Las tarifas de cada categoría y el porcentaje del recargo los fija la
Coordinación de Soporte y [...] se los cambian casi cada semestre y casi nunca
con tiempo." Por eso son *datos con fecha de vigencia* y no constantes del
código: cambiarlos es registrar un tarifario nuevo, sin desplegar (ADR-0006).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from decimal import Decimal

from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.errores import DatoInvalido, SinTarifarioVigente
from compulab.dominio.comun.validacion import texto_requerido
from compulab.dominio.horario.asistente import Categoria

CIEN = Decimal(100)


class Tarifario:
    """Invariantes: tarifa positiva para cada categoría, recargo >= 0, vigencia coherente."""

    def __init__(
        self,
        id: str,
        vigente_desde: date,
        vigente_hasta: date | None,
        tarifas_por_hora: Mapping[Categoria, Dinero],
        porcentaje_recargo: Decimal,
    ) -> None:
        self._id = texto_requerido(id, "id")
        if vigente_hasta is not None and vigente_hasta < vigente_desde:
            raise DatoInvalido("La vigencia del tarifario termina antes de empezar.")
        self._desde = vigente_desde
        self._hasta = vigente_hasta
        faltantes = set(Categoria) - set(tarifas_por_hora)
        if faltantes:
            raise DatoInvalido(f"Falta la tarifa de la categoría {sorted(faltantes)}.")
        if any(t.monto <= 0 for t in tarifas_por_hora.values()):
            raise DatoInvalido("Las tarifas por hora deben ser mayores que cero.")
        self._tarifas = dict(tarifas_por_hora)
        if not isinstance(porcentaje_recargo, Decimal) or porcentaje_recargo < 0:
            raise DatoInvalido("El porcentaje de recargo debe ser un Decimal no negativo.")
        self._porcentaje_recargo = porcentaje_recargo

    @property
    def id(self) -> str:
        return self._id

    @property
    def vigente_desde(self) -> date:
        return self._desde

    @property
    def vigente_hasta(self) -> date | None:
        return self._hasta

    @property
    def porcentaje_recargo(self) -> Decimal:
        return self._porcentaje_recargo

    @property
    def factor_de_recargo(self) -> Decimal:
        """Un recargo del 50 % da un factor de 1,5."""
        return 1 + self._porcentaje_recargo / CIEN

    def tarifa_de(self, categoria: Categoria) -> Dinero:
        return self._tarifas[categoria]

    def aplica_en(self, fecha: date) -> bool:
        return self._desde <= fecha and (self._hasta is None or fecha <= self._hasta)

    def se_traslapa_con(self, otro: Tarifario) -> bool:
        fin_propio = self._hasta or date.max
        fin_otro = otro._hasta or date.max
        return self._desde <= fin_otro and otro._desde <= fin_propio


class CatalogoDeTarifas:
    """Todos los tarifarios. Invariante: sus vigencias no se traslapan.

    Así, para cualquier fecha hay como máximo un tarifario que aplica.
    """

    def __init__(self, tarifarios: Iterable[Tarifario]) -> None:
        lista = sorted(tarifarios, key=lambda t: t.vigente_desde)
        for anterior, siguiente in zip(lista, lista[1:], strict=False):
            if anterior.se_traslapa_con(siguiente):
                raise DatoInvalido(
                    f"Los tarifarios {anterior.id} y {siguiente.id} tienen vigencias traslapadas."
                )
        self._tarifarios = tuple(lista)

    def vigente_en(self, fecha: date) -> Tarifario:
        for tarifario in self._tarifarios:
            if tarifario.aplica_en(fecha):
                return tarifario
        raise SinTarifarioVigente(
            f"No hay tarifas registradas para el {fecha:%d/%m/%Y}; la Coordinación de Soporte "
            "debe registrar el tarifario antes de cerrar el mes."
        )
