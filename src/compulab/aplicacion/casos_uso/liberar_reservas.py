"""CU-16 Liberar reservas no presentadas (extensión 11a de CU-15).

"Si no se presenta dentro de los primeros quince minutos, la reserva se libera
sola y la máquina vuelve a estar disponible para quien llegue." Lo ejecuta una
tarea periódica (cada minuto) que arranca la API; es idempotente, así que no
importa si dos réplicas lo corren a la vez.
"""

from __future__ import annotations

from compulab.aplicacion.puertos import FabricaDeUnidadDeTrabajo, Reloj


class LiberarReservasNoPresentadas:
    def __init__(self, fabrica_uow: FabricaDeUnidadDeTrabajo, reloj: Reloj) -> None:
        self._fabrica_uow = fabrica_uow
        self._reloj = reloj

    def ejecutar(self) -> int:
        """Devuelve cuántas reservas liberó."""
        ahora = self._reloj.ahora()
        liberadas = 0
        with self._fabrica_uow() as uow:
            for reserva in uow.reservas.sin_presentarse(ahora):
                if reserva.liberar_por_ausencia(ahora):
                    uow.reservas.actualizar(reserva)
                    liberadas += 1
            uow.confirmar()
        return liberadas
