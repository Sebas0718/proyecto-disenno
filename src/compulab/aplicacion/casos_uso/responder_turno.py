"""CU-08 Responder turno pendiente (extensión 9a de CU-07).

"...salvo que el propio asistente lo acepte": solo el asistente del turno
puede aceptarlo o rechazarlo. Si lo rechaza, se avisa a quien lo asignó para
que busque a otra persona.
"""

from __future__ import annotations

from dataclasses import dataclass

from compulab.aplicacion.casos_uso.comun import existente, identificar
from compulab.aplicacion.puertos import (
    DirectorioInstitucional,
    FabricaDeUnidadDeTrabajo,
    Notificador,
)
from compulab.dominio.comun.errores import NoAutorizado
from compulab.dominio.horario.turno import EstadoTurno


@dataclass(frozen=True, slots=True)
class ResponderTurnoComando:
    solicitante_id: str
    turno_id: str
    acepta: bool


class ResponderTurnoPendiente:
    def __init__(
        self,
        fabrica_uow: FabricaDeUnidadDeTrabajo,
        directorio: DirectorioInstitucional,
        notificador: Notificador,
    ) -> None:
        self._fabrica_uow = fabrica_uow
        self._directorio = directorio
        self._notificador = notificador

    def ejecutar(self, comando: ResponderTurnoComando) -> EstadoTurno:
        solicitante = identificar(self._directorio, comando.solicitante_id)
        with self._fabrica_uow() as uow:
            turno = existente(uow.turnos.obtener(comando.turno_id), f"el turno {comando.turno_id}")
            if turno.asistente_id != solicitante.id:
                raise NoAutorizado("Solo el asistente del turno puede aceptarlo o rechazarlo.")
            if comando.acepta:
                turno.aceptar()
            else:
                turno.rechazar()
            uow.turnos.actualizar(turno)
            uow.confirmar()

        if turno.estado is EstadoTurno.RECHAZADO:
            i = turno.intervalo
            self._notificador.notificar(
                turno.asignado_por,
                "Turno rechazado por el asistente",
                f"{solicitante.nombre} rechazó el turno del {i.inicio:%d/%m} de "
                f"{i.inicio:%H:%M} a {i.fin:%H:%M} en {turno.laboratorio_id}; "
                "hay que asignarlo a otra persona.",
            )
        return turno.estado
