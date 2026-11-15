"""CU-07 Asignar turno (contrato CO-01, docs/02-casos-de-uso.md).

El caso de uso *coordina*: busca lo que hace falta en los repositorios, deja
que el dominio decida (``PoliticaDeAsignacion``) y guarda el resultado. No
contiene reglas del negocio propias; si las tuviera, no se podrían probar sin
la infraestructura y se repetirían en otros casos de uso.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from compulab.aplicacion.casos_uso.comun import existente, identificar
from compulab.aplicacion.puertos import (
    DirectorioInstitucional,
    FabricaDeUnidadDeTrabajo,
    Notificador,
    Reloj,
)
from compulab.dominio.comun.errores import NoAutorizado
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.horario.politica_asignacion import (
    PoliticaDeAsignacion,
    SolicitudDeAsignacion,
)
from compulab.dominio.horario.turno import EstadoTurno


@dataclass(frozen=True, slots=True)
class AsignarTurnoComando:
    solicitante_id: str
    laboratorio_id: str
    asistente_id: str
    dia: date
    hora_inicio: time
    hora_fin: time


@dataclass(frozen=True, slots=True)
class TurnoAsignado:
    turno_id: str
    estado: EstadoTurno

    @property
    def requiere_aceptacion(self) -> bool:
        return self.estado is EstadoTurno.PENDIENTE_ACEPTACION


class AsignarTurno:
    def __init__(
        self,
        fabrica_uow: FabricaDeUnidadDeTrabajo,
        directorio: DirectorioInstitucional,
        reloj: Reloj,
        notificador: Notificador,
        politica: PoliticaDeAsignacion | None = None,
    ) -> None:
        self._fabrica_uow = fabrica_uow
        self._directorio = directorio
        self._reloj = reloj
        self._notificador = notificador
        self._politica = politica or PoliticaDeAsignacion()

    def ejecutar(self, comando: AsignarTurnoComando) -> TurnoAsignado:
        solicitante = identificar(self._directorio, comando.solicitante_id)
        with self._fabrica_uow() as uow:
            # Paso 4: el laboratorio existe y el solicitante lo puede administrar.
            laboratorio = existente(
                uow.laboratorios.obtener(comando.laboratorio_id),
                f"el laboratorio {comando.laboratorio_id}",
            )
            if not solicitante.puede_administrar_horario(laboratorio.id):
                raise NoAutorizado(
                    f"{solicitante.nombre} no puede modificar el horario de {laboratorio.nombre}."
                )
            # Paso 5: el horario es válido (lo garantiza el constructor del intervalo).
            intervalo = IntervaloTiempo.en_dia(comando.dia, comando.hora_inicio, comando.hora_fin)
            # Pasos 6-10: el dominio verifica las reglas y decide el estado.
            asistente = existente(
                uow.asistentes.obtener(comando.asistente_id, bloquear=True),
                f"el asistente {comando.asistente_id}",
            )
            semana = intervalo.semana.intervalo
            solicitud = SolicitudDeAsignacion(
                asistente=asistente,
                laboratorio_id=laboratorio.id,
                intervalo=intervalo,
                turnos_de_la_semana=tuple(uow.turnos.del_asistente_en(asistente.id, semana)),
                turnos_del_laboratorio=tuple(
                    uow.turnos.del_laboratorio_en(laboratorio.id, intervalo)
                ),
                ahora=self._reloj.ahora(),
            )
            turno = self._politica.asignar(uow.turnos.siguiente_id(), solicitante.id, solicitud)
            # Paso 11: se registra.
            uow.turnos.agregar(turno)
            uow.confirmar()

        if turno.estado is EstadoTurno.PENDIENTE_ACEPTACION:
            self._notificador.notificar(
                asistente.id,
                "Turno pendiente de su aceptación",
                f"{solicitante.nombre} le asignó un turno en {laboratorio.nombre} el "
                f"{intervalo.inicio:%d/%m} de {intervalo.inicio:%H:%M} a {intervalo.fin:%H:%M}, "
                "fuera de la disponibilidad que usted declaró. Acéptelo o recházelo.",
            )
        return TurnoAsignado(turno_id=turno.id, estado=turno.estado)
