"""Consultas de solo lectura para las pantallas.

Se separan de los casos de uso (que *cambian* el estado) siguiendo la idea de
CQRS en su versión más simple: los comandos pasan por las reglas del dominio,
las consultas solo leen. Nunca llaman a ``confirmar()``.

Los permisos de lectura también salen del enunciado: el coordinador de
soporte "ve lo de todos los laboratorios", cada coordinador "solo lo del suyo".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from compulab.aplicacion.casos_uso.comun import existente
from compulab.aplicacion.puertos import FabricaDeUnidadDeTrabajo
from compulab.dominio.comun.errores import NoAutorizado
from compulab.dominio.comun.tiempo import IntervaloTiempo, Mes, SemanaISO
from compulab.dominio.comun.usuario import Rol, Usuario
from compulab.dominio.horario.asistente import Asistente
from compulab.dominio.horario.turno import Turno
from compulab.dominio.pagos.cierre import CierreMensual
from compulab.dominio.reservas.laboratorio import Laboratorio, Maquina
from compulab.dominio.reservas.reserva import Reserva


@dataclass(frozen=True, slots=True)
class CargaSemanal:
    asistente: Asistente
    minutos_asignados: int


@dataclass(frozen=True, slots=True)
class OcupacionMaquina:
    maquina: Maquina
    reservas: tuple[Reserva, ...]


@dataclass(frozen=True, slots=True)
class OcupacionDelDia:
    laboratorio: Laboratorio
    franjas_abiertas: tuple[IntervaloTiempo, ...]
    maquinas: tuple[OcupacionMaquina, ...]


def _dias(desde: date, cantidad: int = 1) -> IntervaloTiempo:
    """Desde ``desde`` a las 00:00 y por ``cantidad`` días completos."""
    inicio = datetime.combine(desde, time.min)
    return IntervaloTiempo(inicio, inicio + timedelta(days=cantidad))


def _exigir_soporte(solicitante: Usuario) -> None:
    if not solicitante.puede_cerrar_mes():
        raise NoAutorizado("Solo la Coordinación de Soporte consulta los cierres de mes.")


def _por_inicio(reserva: Reserva) -> datetime:
    return reserva.intervalo.inicio


def _por_codigo(maquina: Maquina) -> str:
    return maquina.codigo


class Consultas:
    def __init__(self, fabrica_uow: FabricaDeUnidadDeTrabajo) -> None:
        self._fabrica_uow = fabrica_uow

    def laboratorios(self) -> list[Laboratorio]:
        with self._fabrica_uow() as uow:
            return uow.laboratorios.listar()

    def horario(self, solicitante: Usuario, laboratorio_id: str, semana: SemanaISO) -> list[Turno]:
        if not solicitante.puede_administrar_horario(laboratorio_id):
            raise NoAutorizado("Solo puede ver el horario de los laboratorios a su cargo.")
        with self._fabrica_uow() as uow:
            existente(uow.laboratorios.obtener(laboratorio_id), f"el laboratorio {laboratorio_id}")
            turnos = uow.turnos.del_laboratorio_en(laboratorio_id, semana.intervalo)
        return sorted(turnos, key=lambda t: t.intervalo.inicio)

    def asistentes_con_carga(self, solicitante: Usuario, semana: SemanaISO) -> list[CargaSemanal]:
        """Asistentes y cuántas horas ya tienen asignadas esa semana (en todos los labs)."""
        if solicitante.rol is Rol.ESTUDIANTE:
            raise NoAutorizado("Solo los coordinadores consultan la carga de los asistentes.")
        with self._fabrica_uow() as uow:
            resultado = []
            for asistente in uow.asistentes.listar():
                turnos = uow.turnos.del_asistente_en(asistente.id, semana.intervalo)
                minutos = sum(t.intervalo.minutos for t in turnos if t.vigente)
                resultado.append(CargaSemanal(asistente, minutos))
        return sorted(resultado, key=lambda c: c.asistente.nombre)

    def asistente(self, asistente_id: str) -> Asistente | None:
        with self._fabrica_uow() as uow:
            return uow.asistentes.obtener(asistente_id)

    def turnos_del_asistente(self, asistente_id: str, desde: date, dias: int = 28) -> list[Turno]:
        with self._fabrica_uow() as uow:
            turnos = uow.turnos.del_asistente_en(asistente_id, _dias(desde, dias))
        return sorted(turnos, key=lambda t: t.intervalo.inicio)

    def ocupacion(self, laboratorio_id: str, fecha: date) -> OcupacionDelDia:
        dia = _dias(fecha)
        with self._fabrica_uow() as uow:
            laboratorio = existente(
                uow.laboratorios.obtener(laboratorio_id), f"el laboratorio {laboratorio_id}"
            )
            turnos = uow.turnos.del_laboratorio_en(laboratorio_id, dia)
            maquinas = []
            for maquina in sorted(uow.maquinas.del_laboratorio(laboratorio_id), key=_por_codigo):
                del_dia = uow.reservas.de_maquina_en(maquina.id, dia)
                reservas = [r for r in del_dia if r.ocupa_la_maquina]
                maquinas.append(OcupacionMaquina(maquina, tuple(sorted(reservas, key=_por_inicio))))
        abiertas = sorted((t.intervalo for t in turnos if t.confirmado), key=lambda i: i.inicio)
        return OcupacionDelDia(laboratorio, tuple(abiertas), tuple(maquinas))

    def reservas_del_estudiante(self, estudiante_id: str, desde: date) -> list[Reserva]:
        with self._fabrica_uow() as uow:
            reservas = uow.reservas.del_estudiante_en(estudiante_id, _dias(desde, 28))
        return sorted(reservas, key=_por_inicio)

    def cierres(self, solicitante: Usuario) -> list[CierreMensual]:
        _exigir_soporte(solicitante)
        with self._fabrica_uow() as uow:
            return sorted(uow.cierres.listar(), key=lambda c: c.mes, reverse=True)

    def cierre(self, solicitante: Usuario, mes: Mes) -> CierreMensual | None:
        _exigir_soporte(solicitante)
        with self._fabrica_uow() as uow:
            return uow.cierres.obtener(mes)
