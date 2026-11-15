"""Asistencia: lo que de verdad trabajó un asistente en un turno.

"El asistente marca entrada cuando llega y salida cuando se va [...] Lo que se
registra para efectos de pago es lo que estuvo de verdad, no lo que decía el
horario." Se guarda también el inicio *programado* del turno, porque el
recargo depende de cuándo empieza el turno, no de cuándo llegó el asistente.
"""

from __future__ import annotations

from datetime import datetime

from compulab.dominio.comun.errores import DatoInvalido
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.comun.validacion import texto_requerido


class Asistencia:
    """Invariantes: salida posterior a la entrada, y ambas el mismo día."""

    def __init__(
        self,
        id: str,
        turno_id: str,
        asistente_id: str,
        inicio_programado: datetime,
        entrada: datetime,
        salida: datetime,
    ) -> None:
        self._id = texto_requerido(id, "id")
        self._turno_id = texto_requerido(turno_id, "turno_id")
        self._asistente_id = texto_requerido(asistente_id, "asistente_id")
        if not isinstance(inicio_programado, datetime):
            raise DatoInvalido("Falta el inicio programado del turno.")
        self._inicio_programado = inicio_programado
        self._trabajado = IntervaloTiempo(entrada, salida)
        if entrada.date() != salida.date():
            raise DatoInvalido("La entrada y la salida deben ser del mismo día.")

    @property
    def id(self) -> str:
        return self._id

    @property
    def turno_id(self) -> str:
        return self._turno_id

    @property
    def asistente_id(self) -> str:
        return self._asistente_id

    @property
    def inicio_programado(self) -> datetime:
        return self._inicio_programado

    @property
    def trabajado(self) -> IntervaloTiempo:
        return self._trabajado

    @property
    def minutos_trabajados(self) -> int:
        return self._trabajado.minutos
