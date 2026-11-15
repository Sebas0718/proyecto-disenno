"""Cierre mensual: el resultado que se entrega a Becas.

"Un mes cerrado no se vuelve a calcular ni se corrige: si hubo un error, se
arregla por fuera del sistema y se deja constancia." Por eso ``CierreMensual``
no tiene ningún método que lo modifique después de creado, y la base de datos
además lo protege con un trigger (docs/15-diseno-bd.md).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.errores import DatoInvalido, MesNoTerminado
from compulab.dominio.comun.tiempo import Mes
from compulab.dominio.comun.validacion import de_tipo
from compulab.dominio.pagos.liquidacion import LiquidacionAsistente


class CierreMensual:
    """Invariantes: el mes ya terminó y hay a lo sumo una liquidación por asistente."""

    def __init__(
        self, mes: Mes, cerrado_en: datetime, liquidaciones: Iterable[LiquidacionAsistente]
    ) -> None:
        self._mes = de_tipo(mes, Mes, "mes")
        if not mes.termino_en(cerrado_en):
            raise MesNoTerminado(f"El mes {mes} todavía no ha terminado; no se puede cerrar.")
        self._cerrado_en = cerrado_en
        lista = sorted(liquidaciones, key=lambda li: (li.nombre, li.asistente_id))
        ids = [li.asistente_id for li in lista]
        if len(ids) != len(set(ids)):
            raise DatoInvalido("Un cierre tiene a lo sumo una liquidación por asistente.")
        self._liquidaciones = tuple(lista)

    @property
    def mes(self) -> Mes:
        return self._mes

    @property
    def cerrado_en(self) -> datetime:
        return self._cerrado_en

    @property
    def liquidaciones(self) -> tuple[LiquidacionAsistente, ...]:
        return self._liquidaciones

    @property
    def total(self) -> Dinero:
        total = Dinero.cero()
        for liquidacion in self._liquidaciones:
            total += liquidacion.monto
        return total

    @property
    def con_horas_no_pagadas(self) -> tuple[LiquidacionAsistente, ...]:
        return tuple(li for li in self._liquidaciones if li.tiene_horas_no_pagadas)
