"""Usuario: quién es quién, según el directorio institucional.

El sistema no administra usuarios: el directorio del Centro de Cómputo dice el
nombre y el rol de quien entra (ver el puerto ``DirectorioInstitucional``).
Lo que sí es del dominio son las reglas de permiso, porque salen del enunciado:
"El coordinador de laboratorio solo arma y modifica el horario de su
laboratorio. El coordinador de soporte puede ver y modificar el de todos."
"""

from __future__ import annotations

from enum import StrEnum

from compulab.dominio.comun.errores import DatoInvalido
from compulab.dominio.comun.validacion import de_tipo, texto_requerido


class Rol(StrEnum):
    ESTUDIANTE = "ESTUDIANTE"  # incluye a los asistentes: también son estudiantes
    COORDINADOR_LABORATORIO = "COORDINADOR_LABORATORIO"
    COORDINADOR_SOPORTE = "COORDINADOR_SOPORTE"


class Usuario:
    """Persona identificada por el directorio institucional.

    Invariante: un coordinador de laboratorio tiene exactamente un laboratorio
    a cargo; nadie más tiene laboratorio asociado.
    """

    def __init__(self, id: str, nombre: str, rol: Rol, laboratorio_id: str | None = None) -> None:
        self._id = texto_requerido(id, "id")
        self._nombre = texto_requerido(nombre, "nombre")
        self._rol = de_tipo(rol, Rol, "rol")
        if rol is Rol.COORDINADOR_LABORATORIO:
            self._laboratorio_id: str | None = texto_requerido(laboratorio_id, "laboratorio_id")
        elif laboratorio_id is not None:
            raise DatoInvalido("Solo un coordinador de laboratorio tiene laboratorio a cargo.")
        else:
            self._laboratorio_id = None

    @property
    def id(self) -> str:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def rol(self) -> Rol:
        return self._rol

    @property
    def laboratorio_id(self) -> str | None:
        return self._laboratorio_id

    def puede_administrar_horario(self, laboratorio_id: str) -> bool:
        if self._rol is Rol.COORDINADOR_SOPORTE:
            return True
        return self._rol is Rol.COORDINADOR_LABORATORIO and self._laboratorio_id == laboratorio_id

    def puede_reservar(self) -> bool:
        return self._rol is Rol.ESTUDIANTE

    def puede_cerrar_mes(self) -> bool:
        return self._rol is Rol.COORDINADOR_SOPORTE

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, Usuario) and otro._id == self._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"Usuario({self._id!r}, {self._rol.value})"
