"""Reserva de una máquina por un estudiante.

Invariantes del constructor:
- "Una reserva no puede pasar de dos horas."
- Empieza y termina el mismo día.

Máquina de estados:

    ACTIVA --registrar_llegada()------------> EN_USO
    ACTIVA --liberar_por_ausencia() (15 min)-> LIBERADA
    ACTIVA --cancelar()----------------------> CANCELADA
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from compulab.dominio.comun.errores import DatoInvalido, ReservaMuyLarga, TransicionInvalida
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.comun.validacion import de_tipo, texto_requerido

DURACION_MAXIMA = timedelta(hours=2)
TOLERANCIA_DE_LLEGADA = timedelta(minutes=15)


class EstadoReserva(StrEnum):
    ACTIVA = "ACTIVA"
    EN_USO = "EN_USO"
    LIBERADA = "LIBERADA"
    CANCELADA = "CANCELADA"


class Reserva:
    def __init__(
        self,
        id: str,
        estudiante_id: str,
        maquina_id: str,
        intervalo: IntervaloTiempo,
        estado: EstadoReserva = EstadoReserva.ACTIVA,
    ) -> None:
        self._id = texto_requerido(id, "id")
        self._estudiante_id = texto_requerido(estudiante_id, "estudiante_id")
        self._maquina_id = texto_requerido(maquina_id, "maquina_id")
        self._intervalo = de_tipo(intervalo, IntervaloTiempo, "intervalo")
        if intervalo.duracion > DURACION_MAXIMA:
            raise ReservaMuyLarga(
                f"Una reserva no puede pasar de 2 horas (pidió {intervalo.minutos} minutos)."
            )
        if intervalo.inicio.date() != intervalo.fin.date():
            raise DatoInvalido("Una reserva empieza y termina el mismo día.")
        self._estado = de_tipo(estado, EstadoReserva, "estado")

    @property
    def id(self) -> str:
        return self._id

    @property
    def estudiante_id(self) -> str:
        return self._estudiante_id

    @property
    def maquina_id(self) -> str:
        return self._maquina_id

    @property
    def intervalo(self) -> IntervaloTiempo:
        return self._intervalo

    @property
    def estado(self) -> EstadoReserva:
        return self._estado

    @property
    def limite_de_llegada(self) -> datetime:
        """Si no se presenta antes de esta hora, la reserva se libera sola."""
        return self._intervalo.inicio + TOLERANCIA_DE_LLEGADA

    @property
    def ocupa_la_maquina(self) -> bool:
        return self._estado in (EstadoReserva.ACTIVA, EstadoReserva.EN_USO)

    @property
    def cuenta_para_el_limite_semanal(self) -> bool:
        """Las canceladas no cuentan; las liberadas por ausencia sí (ADR-0010)."""
        return self._estado is not EstadoReserva.CANCELADA

    def esta_activa_en(self, ahora: datetime) -> bool:
        """Activa = ocupa la máquina y todavía no terminó."""
        return self.ocupa_la_maquina and self._intervalo.fin > ahora

    def registrar_llegada(self, ahora: datetime) -> None:
        if self._estado is not EstadoReserva.ACTIVA:
            raise TransicionInvalida(f"La reserva está {self._estado}; no se puede ocupar.")
        if not self._intervalo.inicio <= ahora < self.limite_de_llegada:
            raise TransicionInvalida(
                "La llegada se registra entre el inicio de la reserva y los 15 minutos siguientes."
            )
        self._estado = EstadoReserva.EN_USO

    def liberar_por_ausencia(self, ahora: datetime) -> bool:
        """Libera la reserva si pasaron 15 minutos sin que el estudiante llegara.

        Devuelve True si la liberó. Es idempotente: llamarla dos veces no falla.
        """
        if self._estado is EstadoReserva.ACTIVA and ahora >= self.limite_de_llegada:
            self._estado = EstadoReserva.LIBERADA
            return True
        return False

    def cancelar(self) -> None:
        if self._estado is not EstadoReserva.ACTIVA:
            raise TransicionInvalida(f"La reserva está {self._estado}; no se puede cancelar.")
        self._estado = EstadoReserva.CANCELADA

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, Reserva) and otro._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        i = self._intervalo
        return (
            f"Reserva({self._id!r}, {self._maquina_id}, {i.inicio:%Y-%m-%d %H:%M}-{i.fin:%H:%M}, "
            f"{self._estado.value})"
        )
