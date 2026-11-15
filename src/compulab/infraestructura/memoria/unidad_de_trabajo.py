"""Adaptadores en memoria: repositorios y unidad de trabajo con diccionarios.

Sirven para dos cosas:
1. Como *dobles de prueba* (fakes) de los repositorios: las pruebas de los
   casos de uso corren sin base de datos y en milisegundos.
2. Para levantar la API sin Docker (``COMPULAB_ALMACEN=memoria``).

La unidad de trabajo es transaccional de verdad: al entrar copia todo el
almacén y trabaja sobre la copia; ``confirmar()`` reemplaza el almacén con la
copia y, si no se confirma, la copia se descarta. Así las pruebas pueden
verificar que "si falla el exportador, el mes NO queda cerrado".
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from types import TracebackType
from typing import Self

from compulab.dominio.comun.errores import (
    LaboratorioYaCubierto,
    MaquinaOcupada,
    MesYaCerrado,
    TraslapeDeTurno,
)
from compulab.dominio.comun.tiempo import IntervaloTiempo, Mes
from compulab.dominio.horario.asistente import Asistente
from compulab.dominio.horario.turno import EstadoTurno, Turno
from compulab.dominio.pagos.asistencia import Asistencia
from compulab.dominio.pagos.cierre import CierreMensual
from compulab.dominio.pagos.tarifario import Tarifario
from compulab.dominio.reservas.laboratorio import Laboratorio, Maquina
from compulab.dominio.reservas.reserva import EstadoReserva, Reserva


@dataclass
class AlmacenEnMemoria:
    """El "disco" de los adaptadores en memoria."""

    laboratorios: dict[str, Laboratorio] = field(default_factory=dict)
    maquinas: dict[str, Maquina] = field(default_factory=dict)
    asistentes: dict[str, Asistente] = field(default_factory=dict)
    turnos: dict[str, Turno] = field(default_factory=dict)
    reservas: dict[str, Reserva] = field(default_factory=dict)
    asistencias: dict[str, Asistencia] = field(default_factory=dict)
    tarifarios: dict[str, Tarifario] = field(default_factory=dict)
    cierres: dict[Mes, CierreMensual] = field(default_factory=dict)
    contadores: dict[str, int] = field(default_factory=dict)

    def siguiente_id(self, prefijo: str) -> str:
        self.contadores[prefijo] = self.contadores.get(prefijo, 0) + 1
        return f"{prefijo}-{self.contadores[prefijo]}"


def _tocan(intervalo: IntervaloTiempo, periodo: IntervaloTiempo) -> bool:
    return intervalo.se_traslapa_con(periodo)


class _RepositorioLaboratorios:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._a = almacen

    def obtener(self, laboratorio_id: str) -> Laboratorio | None:
        return self._a.laboratorios.get(laboratorio_id)

    def listar(self) -> list[Laboratorio]:
        return sorted(self._a.laboratorios.values(), key=lambda lab: lab.id)

    def agregar(self, laboratorio: Laboratorio) -> None:
        self._a.laboratorios[laboratorio.id] = laboratorio


class _RepositorioMaquinas:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._a = almacen

    def obtener(self, maquina_id: str) -> Maquina | None:
        return self._a.maquinas.get(maquina_id)

    def del_laboratorio(self, laboratorio_id: str) -> list[Maquina]:
        return [m for m in self._a.maquinas.values() if m.laboratorio_id == laboratorio_id]

    def agregar(self, maquina: Maquina) -> None:
        self._a.maquinas[maquina.id] = maquina


class _RepositorioAsistentes:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._a = almacen

    def obtener(self, asistente_id: str, *, bloquear: bool = False) -> Asistente | None:
        return self._a.asistentes.get(asistente_id)  # en memoria no hay concurrencia

    def listar(self) -> list[Asistente]:
        return list(self._a.asistentes.values())

    def agregar(self, asistente: Asistente) -> None:
        self._a.asistentes[asistente.id] = asistente


class _RepositorioTurnos:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._a = almacen

    def siguiente_id(self) -> str:
        return self._a.siguiente_id("T")

    def obtener(self, turno_id: str) -> Turno | None:
        return self._a.turnos.get(turno_id)

    def agregar(self, turno: Turno) -> None:
        # Imita las restricciones de exclusión de PostgreSQL (docs/15-diseno-bd.md).
        for otro in self._a.turnos.values():
            if not (otro.vigente and turno.vigente):
                continue
            if not otro.intervalo.se_traslapa_con(turno.intervalo):
                continue
            if otro.asistente_id == turno.asistente_id:
                raise TraslapeDeTurno("El asistente ya tiene un turno que se traslapa.")
            if otro.laboratorio_id == turno.laboratorio_id:
                raise LaboratorioYaCubierto("El laboratorio ya tiene un turno en esa franja.")
        self._a.turnos[turno.id] = turno

    def actualizar(self, turno: Turno) -> None:
        self._a.turnos[turno.id] = turno

    def del_asistente_en(self, asistente_id: str, periodo: IntervaloTiempo) -> list[Turno]:
        return [
            t
            for t in self._a.turnos.values()
            if t.asistente_id == asistente_id and _tocan(t.intervalo, periodo)
        ]

    def del_laboratorio_en(self, laboratorio_id: str, periodo: IntervaloTiempo) -> list[Turno]:
        return [
            t
            for t in self._a.turnos.values()
            if t.laboratorio_id == laboratorio_id and _tocan(t.intervalo, periodo)
        ]

    def pendientes_del_asistente(self, asistente_id: str) -> list[Turno]:
        return [
            t
            for t in self._a.turnos.values()
            if t.asistente_id == asistente_id and t.estado is EstadoTurno.PENDIENTE_ACEPTACION
        ]


class _RepositorioReservas:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._a = almacen

    def siguiente_id(self) -> str:
        return self._a.siguiente_id("R")

    def agregar(self, reserva: Reserva) -> None:
        for otra in self._a.reservas.values():
            if (
                otra.maquina_id == reserva.maquina_id
                and otra.ocupa_la_maquina
                and otra.intervalo.se_traslapa_con(reserva.intervalo)
            ):
                raise MaquinaOcupada("La máquina ya está reservada en esa franja.")
        self._a.reservas[reserva.id] = reserva

    def actualizar(self, reserva: Reserva) -> None:
        self._a.reservas[reserva.id] = reserva

    def de_maquina_en(self, maquina_id: str, periodo: IntervaloTiempo) -> list[Reserva]:
        return [
            r
            for r in self._a.reservas.values()
            if r.maquina_id == maquina_id and _tocan(r.intervalo, periodo)
        ]

    def del_estudiante_en(self, estudiante_id: str, periodo: IntervaloTiempo) -> list[Reserva]:
        return [
            r
            for r in self._a.reservas.values()
            if r.estudiante_id == estudiante_id and _tocan(r.intervalo, periodo)
        ]

    def activas_del_estudiante(self, estudiante_id: str, ahora: datetime) -> list[Reserva]:
        return [
            r
            for r in self._a.reservas.values()
            if r.estudiante_id == estudiante_id and r.esta_activa_en(ahora)
        ]

    def sin_presentarse(self, ahora: datetime) -> list[Reserva]:
        return [
            r
            for r in self._a.reservas.values()
            if r.estado is EstadoReserva.ACTIVA and r.limite_de_llegada <= ahora
        ]


class _RepositorioAsistencias:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._a = almacen

    def en(self, periodo: IntervaloTiempo) -> list[Asistencia]:
        return [
            a
            for a in self._a.asistencias.values()
            if periodo.inicio <= a.trabajado.inicio < periodo.fin
        ]

    def agregar(self, asistencia: Asistencia) -> None:
        self._a.asistencias[asistencia.id] = asistencia


class _RepositorioTarifarios:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._a = almacen

    def todos(self) -> list[Tarifario]:
        return list(self._a.tarifarios.values())

    def agregar(self, tarifario: Tarifario) -> None:
        self._a.tarifarios[tarifario.id] = tarifario


class _RepositorioCierres:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._a = almacen

    def existe(self, mes: Mes) -> bool:
        return mes in self._a.cierres

    def agregar(self, cierre: CierreMensual) -> None:
        if cierre.mes in self._a.cierres:  # imita la llave primaria (anio, mes)
            raise MesYaCerrado(f"El mes {cierre.mes} ya está cerrado.")
        self._a.cierres[cierre.mes] = cierre

    def obtener(self, mes: Mes) -> CierreMensual | None:
        return self._a.cierres.get(mes)

    def listar(self) -> list[CierreMensual]:
        return list(self._a.cierres.values())


class UnidadDeTrabajoEnMemoria:
    def __init__(self, almacen: AlmacenEnMemoria) -> None:
        self._almacen = almacen
        self._copia: AlmacenEnMemoria | None = None
        self.confirmaciones = 0  # útil en pruebas

    def __enter__(self) -> Self:
        self._copia = copy.deepcopy(self._almacen)
        self.laboratorios = _RepositorioLaboratorios(self._copia)
        self.maquinas = _RepositorioMaquinas(self._copia)
        self.asistentes = _RepositorioAsistentes(self._copia)
        self.turnos = _RepositorioTurnos(self._copia)
        self.reservas = _RepositorioReservas(self._copia)
        self.asistencias = _RepositorioAsistencias(self._copia)
        self.tarifarios = _RepositorioTarifarios(self._copia)
        self.cierres = _RepositorioCierres(self._copia)
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        self._copia = None  # lo no confirmado se descarta

    def confirmar(self) -> None:
        if self._copia is None:
            raise RuntimeError("confirmar() solo se puede llamar dentro del bloque with.")
        self._almacen.__dict__.update(copy.deepcopy(self._copia).__dict__)
        self.confirmaciones += 1


def fabrica_en_memoria(almacen: AlmacenEnMemoria) -> Callable[[], UnidadDeTrabajoEnMemoria]:
    """Devuelve una ``FabricaDeUnidadDeTrabajo`` que comparte el mismo almacén."""
    return lambda: UnidadDeTrabajoEnMemoria(almacen)
