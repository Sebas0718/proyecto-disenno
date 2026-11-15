"""Disponibilidad declarada por el estudiante en su postulación.

"Un estudiante se postula indicando en qué bloques horarios podría trabajar".
Un bloque es semanal (todos los martes de 13:00 a 17:00); la disponibilidad es
el conjunto de bloques.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import time
from enum import IntEnum

from compulab.dominio.comun.errores import DatoInvalido
from compulab.dominio.comun.tiempo import IntervaloTiempo, cubren


class DiaSemana(IntEnum):
    """Mismo número que ``date.weekday()``: lunes = 0, domingo = 6."""

    LUNES = 0
    MARTES = 1
    MIERCOLES = 2
    JUEVES = 3
    VIERNES = 4
    SABADO = 5
    DOMINGO = 6


@dataclass(frozen=True, slots=True)
class BloqueDisponible:
    """Un bloque semanal. Invariante: la hora de fin es posterior a la de inicio."""

    dia: DiaSemana
    hora_inicio: time
    hora_fin: time

    def __post_init__(self) -> None:
        if not isinstance(self.dia, DiaSemana):
            raise DatoInvalido("El día del bloque debe ser un DiaSemana.")
        if self.hora_fin <= self.hora_inicio:
            raise DatoInvalido("Un bloque disponible debe terminar después de empezar.")


class Disponibilidad:
    """Conjunto de bloques declarados. Es inmutable una vez creado."""

    def __init__(self, bloques: Iterable[BloqueDisponible]) -> None:
        self._bloques = tuple(sorted(set(bloques), key=lambda b: (b.dia, b.hora_inicio)))

    @property
    def bloques(self) -> tuple[BloqueDisponible, ...]:
        return self._bloques

    def incluye(self, intervalo: IntervaloTiempo) -> bool:
        """¿Está el intervalo completo dentro de los bloques declarados ese día?

        Bloques seguidos se suman: si declaró 8-10 y 10-12, un turno de 9 a 11
        está dentro de su disponibilidad.
        """
        fecha = intervalo.inicio.date()
        if intervalo.fin.date() != fecha:
            return False
        del_dia = [
            IntervaloTiempo.en_dia(fecha, b.hora_inicio, b.hora_fin)
            for b in self._bloques
            if b.dia == fecha.weekday()
        ]
        return cubren(del_dia, intervalo)
