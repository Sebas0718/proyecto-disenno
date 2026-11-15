"""Laboratorio y Máquina.

``Laboratorio`` no tiene reglas propias (solo identidad, nombre y campus).
``Maquina`` sí: su estado de servicio decide si se puede reservar.
"""

from __future__ import annotations

from enum import StrEnum

from compulab.dominio.comun.errores import TransicionInvalida
from compulab.dominio.comun.validacion import de_tipo, texto_requerido


class Laboratorio:
    def __init__(self, id: str, nombre: str, campus: str) -> None:
        self._id = texto_requerido(id, "id")
        self._nombre = texto_requerido(nombre, "nombre")
        self._campus = texto_requerido(campus, "campus")

    @property
    def id(self) -> str:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def campus(self) -> str:
        return self._campus

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, Laboratorio) and otro._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)


class EstadoMaquina(StrEnum):
    EN_SERVICIO = "EN_SERVICIO"
    FUERA_DE_SERVICIO = "FUERA_DE_SERVICIO"


class Maquina:
    """Una máquina de un laboratorio, con su identificador visible (``codigo``)."""

    def __init__(
        self,
        id: str,
        laboratorio_id: str,
        codigo: str,
        estado: EstadoMaquina = EstadoMaquina.EN_SERVICIO,
    ) -> None:
        self._id = texto_requerido(id, "id")
        self._laboratorio_id = texto_requerido(laboratorio_id, "laboratorio_id")
        self._codigo = texto_requerido(codigo, "codigo")
        self._estado = de_tipo(estado, EstadoMaquina, "estado")

    @property
    def id(self) -> str:
        return self._id

    @property
    def laboratorio_id(self) -> str:
        return self._laboratorio_id

    @property
    def codigo(self) -> str:
        return self._codigo

    @property
    def estado(self) -> EstadoMaquina:
        return self._estado

    @property
    def en_servicio(self) -> bool:
        return self._estado is EstadoMaquina.EN_SERVICIO

    def marcar_fuera_de_servicio(self) -> None:
        if not self.en_servicio:
            raise TransicionInvalida(f"La máquina {self._codigo} ya está fuera de servicio.")
        self._estado = EstadoMaquina.FUERA_DE_SERVICIO

    def marcar_reparada(self) -> None:
        if self.en_servicio:
            raise TransicionInvalida(f"La máquina {self._codigo} ya está en servicio.")
        self._estado = EstadoMaquina.EN_SERVICIO

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, Maquina) and otro._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)
