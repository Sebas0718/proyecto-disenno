"""CU-15 Reservar máquina (contrato CO-02, docs/02-casos-de-uso.md)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from compulab.aplicacion.casos_uso.comun import existente, identificar
from compulab.aplicacion.puertos import DirectorioInstitucional, FabricaDeUnidadDeTrabajo, Reloj
from compulab.dominio.comun.errores import NoAutorizado
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.reservas.politica_reserva import PoliticaDeReserva, SolicitudDeReserva
from compulab.dominio.reservas.reserva import EstadoReserva, Reserva


@dataclass(frozen=True, slots=True)
class ReservarMaquinaComando:
    solicitante_id: str
    maquina_id: str
    inicio: datetime
    fin: datetime


@dataclass(frozen=True, slots=True)
class ReservaRegistrada:
    reserva_id: str
    estado: EstadoReserva
    limite_de_llegada: datetime


class ReservarMaquina:
    def __init__(
        self,
        fabrica_uow: FabricaDeUnidadDeTrabajo,
        directorio: DirectorioInstitucional,
        reloj: Reloj,
        politica: PoliticaDeReserva | None = None,
    ) -> None:
        self._fabrica_uow = fabrica_uow
        self._directorio = directorio
        self._reloj = reloj
        self._politica = politica or PoliticaDeReserva()

    def ejecutar(self, comando: ReservarMaquinaComando) -> ReservaRegistrada:
        # Paso 4: solo estudiantes de la Escuela reservan.
        estudiante = identificar(self._directorio, comando.solicitante_id)
        if not estudiante.puede_reservar():
            raise NoAutorizado("Solo los estudiantes de la Escuela pueden reservar máquinas.")
        ahora = self._reloj.ahora()
        with self._fabrica_uow() as uow:
            # Paso 5: la máquina existe.
            maquina = existente(
                uow.maquinas.obtener(comando.maquina_id), f"la máquina {comando.maquina_id}"
            )
            # Paso 6: franja válida y de máximo 2 horas (invariantes de la Reserva).
            intervalo = IntervaloTiempo(comando.inicio, comando.fin)
            candidata = Reserva(
                id=uow.reservas.siguiente_id(),
                estudiante_id=estudiante.id,
                maquina_id=maquina.id,
                intervalo=intervalo,
            )
            # Pasos 5b y 7-10: las reglas del dominio.
            solicitud = SolicitudDeReserva(
                reserva=candidata,
                maquina=maquina,
                ahora=ahora,
                turnos_del_laboratorio=tuple(
                    uow.turnos.del_laboratorio_en(maquina.laboratorio_id, intervalo)
                ),
                reservas_de_la_maquina=tuple(uow.reservas.de_maquina_en(maquina.id, intervalo)),
                reservas_activas_del_estudiante=tuple(
                    uow.reservas.activas_del_estudiante(estudiante.id, ahora)
                ),
                reservas_de_la_semana=tuple(
                    uow.reservas.del_estudiante_en(estudiante.id, intervalo.semana.intervalo)
                ),
            )
            self._politica.verificar(solicitud)
            # Paso 11: se registra.
            uow.reservas.agregar(candidata)
            uow.confirmar()
        return ReservaRegistrada(
            reserva_id=candidata.id,
            estado=candidata.estado,
            limite_de_llegada=candidata.limite_de_llegada,
        )
