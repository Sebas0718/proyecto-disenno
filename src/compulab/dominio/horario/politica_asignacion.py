"""Política de asignación de turnos (servicio de dominio).

"Al armarlo hay tres cosas que el sistema no puede dejar pasar":
  1. traslapes con otro turno del mismo asistente (aunque sea en otro
     laboratorio u otro campus);
  2. superar en alguna semana el tope de horas que fijó Becas;
  3. asignar un bloque no declarado como disponible, salvo que el asistente
     lo acepte.

Además, "exactamente una persona responsable [...] ni turnos compartidos entre
dos": un laboratorio no puede tener dos turnos al mismo tiempo (ADR-0008).

Las reglas 1 y 2 (más "asistente activo", "turno futuro" y "un responsable por
laboratorio") son objetos
independientes que cumplen el protocolo ``ReglaDeAsignacion``: es el patrón
Specification / cadena de reglas. Así la misma lista se reutiliza al aprobar un
cambio de turno ("el sistema tiene que verificar otra vez lo mismo"), y se puede
agregar una regla nueva sin tocar las existentes.

La regla 3 no rechaza: decide el estado inicial del turno (ADR-0008).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from compulab.dominio.comun.errores import (
    AsistenteInactivo,
    DatoInvalido,
    EnElPasado,
    LaboratorioYaCubierto,
    TopeSemanalExcedido,
    TraslapeDeTurno,
)
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.horario.asistente import Asistente
from compulab.dominio.horario.turno import EstadoTurno, Turno


def _horas(minutos: int) -> str:
    return f"{minutos / 60:g} h"


@dataclass(frozen=True, slots=True)
class SolicitudDeAsignacion:
    """Todo lo que las reglas necesitan saber para decidir.

    - ``turnos_de_la_semana``: los turnos del asistente, en cualquier
      laboratorio, de la semana ISO del turno nuevo.
    - ``turnos_del_laboratorio``: los turnos del laboratorio que tocan el
      intervalo del turno nuevo (de cualquier asistente).
    """

    asistente: Asistente
    laboratorio_id: str
    intervalo: IntervaloTiempo
    turnos_de_la_semana: tuple[Turno, ...]
    turnos_del_laboratorio: tuple[Turno, ...]
    ahora: datetime

    def __post_init__(self) -> None:
        if any(t.asistente_id != self.asistente.id for t in self.turnos_de_la_semana):
            raise DatoInvalido("Los turnos de la semana deben ser del mismo asistente.")
        if any(t.laboratorio_id != self.laboratorio_id for t in self.turnos_del_laboratorio):
            raise DatoInvalido("Los turnos del laboratorio deben ser de ese laboratorio.")

    @property
    def turnos_vigentes(self) -> list[Turno]:
        return [t for t in self.turnos_de_la_semana if t.vigente]


class ReglaDeAsignacion(Protocol):
    """Una regla lanza un ErrorDeDominio si la solicitud la incumple."""

    def verificar(self, solicitud: SolicitudDeAsignacion) -> None: ...


class TurnoDebeSerFuturo:
    def verificar(self, solicitud: SolicitudDeAsignacion) -> None:
        if solicitud.intervalo.inicio <= solicitud.ahora:
            raise EnElPasado("No se puede asignar un turno que ya empezó o que ya pasó.")


class AsistenteDebeEstarActivo:
    def verificar(self, solicitud: SolicitudDeAsignacion) -> None:
        asistente = solicitud.asistente
        if not asistente.esta_activo:
            raise AsistenteInactivo(
                f"{asistente.nombre} no está activo ({asistente.estado}); "
                "no se le pueden asignar turnos nuevos."
            )


class SinTraslapes:
    def verificar(self, solicitud: SolicitudDeAsignacion) -> None:
        for turno in solicitud.turnos_vigentes:
            if turno.intervalo.se_traslapa_con(solicitud.intervalo):
                i = turno.intervalo
                raise TraslapeDeTurno(
                    f"{solicitud.asistente.nombre} ya tiene un turno en {turno.laboratorio_id} "
                    f"el {i.inicio:%d/%m} de {i.inicio:%H:%M} a {i.fin:%H:%M}."
                )


class UnResponsablePorLaboratorio:
    def verificar(self, solicitud: SolicitudDeAsignacion) -> None:
        for turno in solicitud.turnos_del_laboratorio:
            if turno.vigente and turno.intervalo.se_traslapa_con(solicitud.intervalo):
                i = turno.intervalo
                raise LaboratorioYaCubierto(
                    f"{solicitud.laboratorio_id} ya tiene un turno de {i.inicio:%H:%M} a "
                    f"{i.fin:%H:%M} ese día; un turno tiene un solo responsable."
                )


class DentroDelTopeSemanal:
    def verificar(self, solicitud: SolicitudDeAsignacion) -> None:
        semana = solicitud.intervalo.semana
        asignados = sum(
            t.intervalo.minutos for t in solicitud.turnos_vigentes if t.intervalo.semana == semana
        )
        total = asignados + solicitud.intervalo.minutos
        tope = solicitud.asistente.tope_minutos_semanales
        if total > tope:
            raise TopeSemanalExcedido(
                f"{solicitud.asistente.nombre} ya tiene {_horas(asignados)} en la semana {semana}; "
                f"con este turno llegaría a {_horas(total)} y su tope es {_horas(tope)}."
            )


REGLAS_DE_ASIGNACION: tuple[ReglaDeAsignacion, ...] = (
    TurnoDebeSerFuturo(),
    AsistenteDebeEstarActivo(),
    SinTraslapes(),
    UnResponsablePorLaboratorio(),
    DentroDelTopeSemanal(),
)


class PoliticaDeAsignacion:
    """Verifica las reglas y fabrica el turno con el estado inicial correcto."""

    def __init__(self, reglas: Sequence[ReglaDeAsignacion] = REGLAS_DE_ASIGNACION) -> None:
        self._reglas = tuple(reglas)

    def verificar(self, solicitud: SolicitudDeAsignacion) -> None:
        for regla in self._reglas:
            regla.verificar(solicitud)

    def asignar(self, turno_id: str, asignado_por: str, solicitud: SolicitudDeAsignacion) -> Turno:
        self.verificar(solicitud)
        if solicitud.asistente.declaro_disponible(solicitud.intervalo):
            estado = EstadoTurno.CONFIRMADO
        else:
            estado = EstadoTurno.PENDIENTE_ACEPTACION
        return Turno(
            id=turno_id,
            laboratorio_id=solicitud.laboratorio_id,
            asistente_id=solicitud.asistente.id,
            intervalo=solicitud.intervalo,
            estado=estado,
            asignado_por=asignado_por,
        )
