"""Asistente: estudiante admitido para trabajar por turnos.

Reglas del enunciado que viven aquí:
- "A un asistente que ya no está activo no se le puede asignar ningún turno".
- La categoría (dos, cada una con su tarifa) y el tope semanal de horas que
  fija Becas se registran al admitirlo; el tope se puede corregir después.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from compulab.dominio.comun.errores import DatoInvalido, TransicionInvalida
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.comun.validacion import de_tipo, texto_requerido
from compulab.dominio.horario.disponibilidad import Disponibilidad

HORAS_POR_SEMANA = Decimal(168)


class Categoria(StrEnum):
    """Las dos categorías de asistente; cada una tiene su tarifa por hora."""

    A = "A"
    B = "B"


class EstadoAsistente(StrEnum):
    ACTIVO = "ACTIVO"
    RENUNCIO = "RENUNCIO"
    DADO_DE_BAJA = "DADO_DE_BAJA"


def _validar_tope(tope: object) -> Decimal:
    if not isinstance(tope, Decimal) or not tope.is_finite():
        raise DatoInvalido("El tope de horas semanales debe ser un Decimal.")
    if not Decimal(0) < tope <= HORAS_POR_SEMANA:
        raise DatoInvalido(f"El tope semanal debe estar entre 0 y 168 horas (llegó {tope}).")
    return tope


class Asistente:
    """Entidad con identidad propia (su carné / id del directorio)."""

    def __init__(
        self,
        id: str,
        nombre: str,
        categoria: Categoria,
        tope_horas_semanales: Decimal,
        disponibilidad: Disponibilidad,
        estado: EstadoAsistente = EstadoAsistente.ACTIVO,
    ) -> None:
        self._id = texto_requerido(id, "id")
        self._nombre = texto_requerido(nombre, "nombre")
        self._categoria = de_tipo(categoria, Categoria, "categoria")
        self._tope = _validar_tope(tope_horas_semanales)
        self._disponibilidad = de_tipo(disponibilidad, Disponibilidad, "disponibilidad")
        self._estado = de_tipo(estado, EstadoAsistente, "estado")

    # --- lectura ---------------------------------------------------------------
    @property
    def id(self) -> str:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def categoria(self) -> Categoria:
        return self._categoria

    @property
    def tope_horas_semanales(self) -> Decimal:
        return self._tope

    @property
    def tope_minutos_semanales(self) -> int:
        return int(self._tope * 60)

    @property
    def disponibilidad(self) -> Disponibilidad:
        return self._disponibilidad

    @property
    def estado(self) -> EstadoAsistente:
        return self._estado

    @property
    def esta_activo(self) -> bool:
        return self._estado is EstadoAsistente.ACTIVO

    # --- comportamiento --------------------------------------------------------
    def declaro_disponible(self, intervalo: IntervaloTiempo) -> bool:
        return self._disponibilidad.incluye(intervalo)

    def corregir_tope(self, nuevo_tope: Decimal) -> None:
        """Becas cambió el tope; el coordinador de soporte lo corrige."""
        self._tope = _validar_tope(nuevo_tope)

    def renunciar(self) -> None:
        self._dejar_de_estar_activo(EstadoAsistente.RENUNCIO)

    def dar_de_baja(self) -> None:
        self._dejar_de_estar_activo(EstadoAsistente.DADO_DE_BAJA)

    def _dejar_de_estar_activo(self, nuevo: EstadoAsistente) -> None:
        if not self.esta_activo:
            raise TransicionInvalida(f"{self._nombre} ya no está activo ({self._estado}).")
        self._estado = nuevo

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, Asistente) and otro._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Asistente({self._id!r}, {self._categoria.value}, {self._estado.value})"
