"""Turno: un laboratorio, un día, una hora de inicio, una de fin y un responsable.

"No existen turnos sin asistente ni turnos compartidos entre dos": por eso el
constructor exige exactamente un ``asistente_id``.

Máquina de estados (patrón State, versión simple con un Enum):

    PENDIENTE_ACEPTACION --aceptar()--> CONFIRMADO
    PENDIENTE_ACEPTACION --rechazar()-> RECHAZADO
    (se crea CONFIRMADO directamente si el bloque estaba en la disponibilidad)
"""

from __future__ import annotations

from enum import StrEnum

from compulab.dominio.comun.errores import DatoInvalido, TransicionInvalida
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.comun.validacion import de_tipo, texto_requerido


class EstadoTurno(StrEnum):
    PENDIENTE_ACEPTACION = "PENDIENTE_ACEPTACION"
    CONFIRMADO = "CONFIRMADO"
    RECHAZADO = "RECHAZADO"


class Turno:
    def __init__(
        self,
        id: str,
        laboratorio_id: str,
        asistente_id: str,
        intervalo: IntervaloTiempo,
        estado: EstadoTurno,
        asignado_por: str,
    ) -> None:
        self._id = texto_requerido(id, "id")
        self._laboratorio_id = texto_requerido(laboratorio_id, "laboratorio_id")
        self._asistente_id = texto_requerido(asistente_id, "asistente_id")
        self._intervalo = de_tipo(intervalo, IntervaloTiempo, "intervalo")
        if intervalo.inicio.date() != intervalo.fin.date():
            raise DatoInvalido("Un turno empieza y termina el mismo día.")
        self._estado = de_tipo(estado, EstadoTurno, "estado")
        self._asignado_por = texto_requerido(asignado_por, "asignado_por")

    @property
    def id(self) -> str:
        return self._id

    @property
    def laboratorio_id(self) -> str:
        return self._laboratorio_id

    @property
    def asistente_id(self) -> str:
        return self._asistente_id

    @property
    def intervalo(self) -> IntervaloTiempo:
        return self._intervalo

    @property
    def estado(self) -> EstadoTurno:
        return self._estado

    @property
    def asignado_por(self) -> str:
        return self._asignado_por

    @property
    def vigente(self) -> bool:
        """Un turno vigente ocupa el tiempo del asistente y cuenta para su tope.

        Los pendientes también cuentan: si no, se podrían crear dos pendientes
        que se traslapan y el asistente terminaría aceptando ambos.
        """
        return self._estado is not EstadoTurno.RECHAZADO

    @property
    def confirmado(self) -> bool:
        """Solo un turno confirmado abre el laboratorio."""
        return self._estado is EstadoTurno.CONFIRMADO

    def aceptar(self) -> None:
        self._salir_de_pendiente(EstadoTurno.CONFIRMADO)

    def rechazar(self) -> None:
        self._salir_de_pendiente(EstadoTurno.RECHAZADO)

    def _salir_de_pendiente(self, nuevo: EstadoTurno) -> None:
        if self._estado is not EstadoTurno.PENDIENTE_ACEPTACION:
            raise TransicionInvalida(
                f"El turno ya no está pendiente de aceptación (está {self._estado})."
            )
        self._estado = nuevo

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, Turno) and otro._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        i = self._intervalo
        return (
            f"Turno({self._id!r}, {self._laboratorio_id}, {i.inicio:%Y-%m-%d %H:%M}-"
            f"{i.fin:%H:%M}, {self._asistente_id}, {self._estado.value})"
        )
