"""Objetos de valor de tiempo: IntervaloTiempo, SemanaISO y Mes.

Todas las fechas y horas son *hora local* de Costa Rica sin zona horaria
(ver ADR-0009). El dominio nunca pregunta "qué hora es": la recibe.

Los objetos de valor son inmutables (``frozen=True``): no se pueden modificar
después de creados, así que una invariante verificada en el constructor se
cumple para siempre.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from compulab.dominio.comun.errores import DatoInvalido, IntervaloInvalido

UN_MINUTO = timedelta(minutes=1)


@dataclass(frozen=True, slots=True)
class IntervaloTiempo:
    """Un tramo de tiempo [inicio, fin): incluye el inicio y excluye el fin.

    Invariante: ``fin`` es estrictamente posterior a ``inicio``.
    """

    inicio: datetime
    fin: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.inicio, datetime) or not isinstance(self.fin, datetime):
            raise DatoInvalido("Un intervalo necesita fecha y hora de inicio y de fin.")
        if self.inicio.tzinfo is not None or self.fin.tzinfo is not None:
            raise DatoInvalido("Las horas se manejan en hora local, sin zona horaria.")
        if self.fin <= self.inicio:
            raise IntervaloInvalido(
                f"La hora de fin ({self.fin:%H:%M}) debe ser posterior a la de inicio "
                f"({self.inicio:%H:%M})."
            )

    @classmethod
    def en_dia(cls, dia: date, hora_inicio: time, hora_fin: time) -> IntervaloTiempo:
        """Crea un intervalo que empieza y termina el mismo día."""
        return cls(datetime.combine(dia, hora_inicio), datetime.combine(dia, hora_fin))

    @property
    def duracion(self) -> timedelta:
        return self.fin - self.inicio

    @property
    def minutos(self) -> int:
        """Duración en minutos completos (las horas se cuentan por minuto)."""
        return self.duracion // UN_MINUTO

    @property
    def semana(self) -> SemanaISO:
        """Semana ISO en la que empieza el intervalo."""
        return SemanaISO.de(self.inicio.date())

    def se_traslapa_con(self, otro: IntervaloTiempo) -> bool:
        """Dos intervalos se traslapan si comparten algún instante.

        Turnos seguidos (uno termina 10:00 y el otro empieza 10:00) NO se traslapan.
        """
        return self.inicio < otro.fin and otro.inicio < self.fin

    def contiene(self, otro: IntervaloTiempo) -> bool:
        return self.inicio <= otro.inicio and otro.fin <= self.fin


def cubren(intervalos: Iterable[IntervaloTiempo], objetivo: IntervaloTiempo) -> bool:
    """¿Cubren los ``intervalos``, juntos y sin huecos, todo el ``objetivo``?

    Se usa, por ejemplo, para saber si un laboratorio está abierto durante toda
    una reserva: dos turnos seguidos (8-10 y 10-12) cubren una reserva de 9 a 11.
    """
    cursor = objetivo.inicio
    for intervalo in sorted(intervalos, key=lambda i: i.inicio):
        if intervalo.fin <= cursor:
            continue
        if intervalo.inicio > cursor:
            return False  # quedó un hueco sin cubrir
        cursor = intervalo.fin
        if cursor >= objetivo.fin:
            return True
    return cursor >= objetivo.fin


@dataclass(frozen=True, slots=True, order=True)
class SemanaISO:
    """Semana de lunes a domingo según ISO 8601 (ADR-0007)."""

    anio: int
    numero: int

    def __post_init__(self) -> None:
        try:
            date.fromisocalendar(self.anio, self.numero, 1)
        except (ValueError, TypeError) as error:
            raise DatoInvalido(f"La semana {self.anio}-W{self.numero} no existe.") from error

    @classmethod
    def de(cls, fecha: date) -> SemanaISO:
        anio, numero, _ = fecha.isocalendar()
        return cls(anio, numero)

    @property
    def lunes(self) -> date:
        return date.fromisocalendar(self.anio, self.numero, 1)

    @property
    def intervalo(self) -> IntervaloTiempo:
        """Desde el lunes 00:00 hasta el lunes siguiente 00:00."""
        inicio = datetime.combine(self.lunes, time.min)
        return IntervaloTiempo(inicio, inicio + timedelta(days=7))

    def __str__(self) -> str:
        return f"{self.anio}-W{self.numero:02d}"


@dataclass(frozen=True, slots=True, order=True)
class Mes:
    """Un mes calendario; la unidad del cierre de pago."""

    anio: int
    numero: int

    def __post_init__(self) -> None:
        if not isinstance(self.numero, int) or not 1 <= self.numero <= 12:
            raise DatoInvalido(f"El mes {self.numero} no existe; debe estar entre 1 y 12.")
        if not isinstance(self.anio, int) or not 2000 <= self.anio <= 2100:
            raise DatoInvalido(f"El año {self.anio} está fuera de rango.")

    @classmethod
    def de(cls, fecha: date) -> Mes:
        return cls(fecha.year, fecha.month)

    @property
    def primer_dia(self) -> date:
        return date(self.anio, self.numero, 1)

    def siguiente(self) -> Mes:
        if self.numero == 12:
            return Mes(self.anio + 1, 1)
        return Mes(self.anio, self.numero + 1)

    @property
    def intervalo(self) -> IntervaloTiempo:
        """Desde el día 1 a las 00:00 hasta el día 1 del mes siguiente a las 00:00."""
        return IntervaloTiempo(
            datetime.combine(self.primer_dia, time.min),
            datetime.combine(self.siguiente().primer_dia, time.min),
        )

    def contiene(self, fecha: date) -> bool:
        return (fecha.year, fecha.month) == (self.anio, self.numero)

    def termino_en(self, ahora: datetime) -> bool:
        """El mes terminó si ya empezó el mes siguiente."""
        return ahora >= self.intervalo.fin

    def __str__(self) -> str:
        return f"{self.anio}-{self.numero:02d}"
