"""Estrategia de recargo (patrón Strategy).

"Las horas de turnos que empiezan a las seis de la tarde o después, y las de
sábado y domingo, se pagan con un recargo." El *porcentaje* es un dato del
tarifario; la *regla* de qué horas llevan recargo es esta estrategia. Si
mañana la Coordinación cambia la regla (por ejemplo, feriados), se escribe otra
clase que cumpla ``PoliticaDeRecargo`` y se inyecta, sin tocar el cálculo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Protocol

from compulab.dominio.horario.disponibilidad import DiaSemana
from compulab.dominio.pagos.asistencia import Asistencia


class PoliticaDeRecargo(Protocol):
    def aplica(self, asistencia: Asistencia) -> bool: ...


@dataclass(frozen=True, slots=True)
class RecargoNocturnoOFinDeSemana:
    """Recargo una sola vez si el turno es nocturno O de fin de semana (ADR-0008).

    Un turno de sábado a las 19:00 cumple las dos condiciones, pero el recargo
    no se acumula.
    """

    hora_nocturna: time = time(18, 0)

    def aplica(self, asistencia: Asistencia) -> bool:
        inicio = asistencia.inicio_programado
        es_nocturno = inicio.time() >= self.hora_nocturna
        es_fin_de_semana = inicio.weekday() >= DiaSemana.SABADO
        return es_nocturno or es_fin_de_semana
