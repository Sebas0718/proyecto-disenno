"""Ayudas compartidas por los casos de uso."""

from __future__ import annotations

from compulab.aplicacion.puertos import DirectorioInstitucional
from compulab.dominio.comun.errores import NoAutorizado, NoEncontrado
from compulab.dominio.comun.usuario import Usuario


def identificar(directorio: DirectorioInstitucional, usuario_id: str) -> Usuario:
    """Precondición de todos los casos de uso: el solicitante está en el directorio."""
    usuario = directorio.buscar(usuario_id)
    if usuario is None:
        raise NoAutorizado("No se pudo identificar al usuario en el directorio institucional.")
    return usuario


def existente[T](valor: T | None, descripcion: str) -> T:
    """Convierte un ``None`` de un repositorio en el error de dominio NoEncontrado."""
    if valor is None:
        raise NoEncontrado(f"No existe {descripcion}.")
    return valor
