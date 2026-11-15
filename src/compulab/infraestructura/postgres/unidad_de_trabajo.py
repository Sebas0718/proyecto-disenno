"""Unidad de trabajo sobre una conexión PostgreSQL (una transacción por uso).

Cada ``with fabrica() as uow:`` abre una conexión, todos los repositorios la
comparten y, al salir, se hace ``rollback`` de lo que no se confirmó y se
cierra la conexión. ``confirmar()`` hace ``commit``.

Mejora futura (anotada en docs/05-arquitectura.md): usar un *pool* de
conexiones (psycopg_pool) para no abrir una conexión por petición.
"""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Any, Self

import psycopg
from psycopg.rows import dict_row

from compulab.infraestructura.postgres.repositorios import (
    Fila,
    RepositorioAsistenciasPostgres,
    RepositorioAsistentesPostgres,
    RepositorioCierresPostgres,
    RepositorioLaboratoriosPostgres,
    RepositorioMaquinasPostgres,
    RepositorioReservasPostgres,
    RepositorioTarifariosPostgres,
    RepositorioTurnosPostgres,
)

Conectar = Callable[[], psycopg.Connection[Fila]]


class UnidadDeTrabajoPostgres:
    def __init__(self, conectar: Conectar) -> None:
        self._conectar = conectar
        self._conexion: psycopg.Connection[Fila] | None = None

    def __enter__(self) -> Self:
        conexion = self._conectar()
        self._conexion = conexion
        self.laboratorios = RepositorioLaboratoriosPostgres(conexion)
        self.maquinas = RepositorioMaquinasPostgres(conexion)
        self.asistentes = RepositorioAsistentesPostgres(conexion)
        self.turnos = RepositorioTurnosPostgres(conexion)
        self.reservas = RepositorioReservasPostgres(conexion)
        self.asistencias = RepositorioAsistenciasPostgres(conexion)
        self.tarifarios = RepositorioTarifariosPostgres(conexion)
        self.cierres = RepositorioCierresPostgres(conexion)
        return self

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        if self._conexion is not None:
            self._conexion.rollback()  # no hace nada si ya se confirmó
            self._conexion.close()
            self._conexion = None

    def confirmar(self) -> None:
        if self._conexion is None:
            raise RuntimeError("confirmar() solo se puede llamar dentro del bloque with.")
        self._conexion.commit()


def fabrica_postgres(url: str, **opciones: Any) -> Callable[[], UnidadDeTrabajoPostgres]:
    """``opciones`` se pasan a psycopg.connect (p. ej. el search_path en las pruebas)."""

    def conectar() -> psycopg.Connection[Fila]:
        return psycopg.connect(url, row_factory=dict_row, **opciones)

    return lambda: UnidadDeTrabajoPostgres(conectar)
