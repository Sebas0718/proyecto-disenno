"""Adaptadores PostgreSQL 14 (repositorios y unidad de trabajo)."""

from compulab.infraestructura.postgres.unidad_de_trabajo import (
    UnidadDeTrabajoPostgres,
    fabrica_postgres,
)

__all__ = ["UnidadDeTrabajoPostgres", "fabrica_postgres"]
