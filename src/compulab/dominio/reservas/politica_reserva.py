"""Política de reserva de máquinas (servicio de dominio).

Reglas del enunciado:
- Solo dentro de una franja en que el laboratorio esté abierto, es decir, con
  un turno de asistente (confirmado) cubriéndola.
- Máximo dos horas (invariante de ``Reserva``).
- Máximo una reserva activa a la vez por estudiante.
- Máximo seis horas reservadas por semana.
- La máquina debe estar en servicio y libre en esa franja.

Mismo patrón que la asignación de turnos: cada regla es un objeto y la
política las recorre en orden.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from compulab.dominio.comun.errores import (
    DatoInvalido,
    EnElPasado,
    LaboratorioCerrado,
    LimiteSemanalDeReservas,
    MaquinaFueraDeServicio,
    MaquinaOcupada,
    ReservaActivaExistente,
)
from compulab.dominio.comun.tiempo import cubren
from compulab.dominio.horario.turno import Turno
from compulab.dominio.reservas.laboratorio import Maquina
from compulab.dominio.reservas.reserva import Reserva

MINUTOS_SEMANALES_MAXIMOS = 6 * 60


@dataclass(frozen=True, slots=True)
class SolicitudDeReserva:
    """La reserva candidata más el contexto que las reglas necesitan.

    - ``turnos_del_laboratorio``: turnos del laboratorio de la máquina que tocan la franja.
    - ``reservas_de_la_maquina``: reservas de esa máquina que tocan la franja.
    - ``reservas_activas_del_estudiante``: las que todavía no terminan.
    - ``reservas_de_la_semana``: las del estudiante en la semana ISO de la reserva.
    """

    reserva: Reserva
    maquina: Maquina
    ahora: datetime
    turnos_del_laboratorio: tuple[Turno, ...]
    reservas_de_la_maquina: tuple[Reserva, ...]
    reservas_activas_del_estudiante: tuple[Reserva, ...]
    reservas_de_la_semana: tuple[Reserva, ...]

    def __post_init__(self) -> None:
        if self.reserva.maquina_id != self.maquina.id:
            raise DatoInvalido("La reserva no corresponde a la máquina de la solicitud.")
        laboratorio = self.maquina.laboratorio_id
        if any(t.laboratorio_id != laboratorio for t in self.turnos_del_laboratorio):
            raise DatoInvalido("Los turnos deben ser del laboratorio de la máquina.")


class ReglaDeReserva(Protocol):
    def verificar(self, solicitud: SolicitudDeReserva) -> None: ...


class MaquinaEnServicio:
    def verificar(self, solicitud: SolicitudDeReserva) -> None:
        if not solicitud.maquina.en_servicio:
            raise MaquinaFueraDeServicio(
                f"La máquina {solicitud.maquina.codigo} está fuera de servicio."
            )


class ReservaFutura:
    def verificar(self, solicitud: SolicitudDeReserva) -> None:
        if solicitud.reserva.intervalo.inicio < solicitud.ahora:
            raise EnElPasado("No se puede reservar una franja que ya empezó.")


class LaboratorioAbierto:
    def verificar(self, solicitud: SolicitudDeReserva) -> None:
        abiertos = [t.intervalo for t in solicitud.turnos_del_laboratorio if t.confirmado]
        if not cubren(abiertos, solicitud.reserva.intervalo):
            raise LaboratorioCerrado(
                "El laboratorio no tiene un turno de asistente que cubra toda esa franja."
            )


class MaquinaLibre:
    def verificar(self, solicitud: SolicitudDeReserva) -> None:
        nueva = solicitud.reserva
        for otra in solicitud.reservas_de_la_maquina:
            if otra.id != nueva.id and otra.ocupa_la_maquina:
                if otra.intervalo.se_traslapa_con(nueva.intervalo):
                    raise MaquinaOcupada(
                        f"La máquina {solicitud.maquina.codigo} ya está reservada de "
                        f"{otra.intervalo.inicio:%H:%M} a {otra.intervalo.fin:%H:%M}."
                    )


class UnaReservaActivaALaVez:
    def verificar(self, solicitud: SolicitudDeReserva) -> None:
        for otra in solicitud.reservas_activas_del_estudiante:
            if otra.esta_activa_en(solicitud.ahora):
                raise ReservaActivaExistente(
                    "Ya tiene una reserva activa "
                    f"({otra.intervalo.inicio:%d/%m %H:%M}); solo se permite una a la vez."
                )


class SeisHorasPorSemana:
    def verificar(self, solicitud: SolicitudDeReserva) -> None:
        semana = solicitud.reserva.intervalo.semana
        usados = sum(
            r.intervalo.minutos
            for r in solicitud.reservas_de_la_semana
            if r.cuenta_para_el_limite_semanal and r.intervalo.semana == semana
        )
        total = usados + solicitud.reserva.intervalo.minutos
        if total > MINUTOS_SEMANALES_MAXIMOS:
            raise LimiteSemanalDeReservas(
                f"Esta semana ya reservó {usados / 60:g} h; con esta llegaría a {total / 60:g} h "
                "y el máximo es 6 h."
            )


REGLAS_DE_RESERVA: tuple[ReglaDeReserva, ...] = (
    MaquinaEnServicio(),
    ReservaFutura(),
    LaboratorioAbierto(),
    MaquinaLibre(),
    UnaReservaActivaALaVez(),
    SeisHorasPorSemana(),
)


class PoliticaDeReserva:
    def __init__(self, reglas: Sequence[ReglaDeReserva] = REGLAS_DE_RESERVA) -> None:
        self._reglas = tuple(reglas)

    def verificar(self, solicitud: SolicitudDeReserva) -> None:
        for regla in self._reglas:
            regla.verificar(solicitud)
