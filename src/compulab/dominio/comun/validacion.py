"""Pequeñas funciones para verificar invariantes en los constructores."""

from compulab.dominio.comun.errores import DatoInvalido


def texto_requerido(valor: object, campo: str) -> str:
    """Devuelve el texto sin espacios sobrantes, o falla si viene vacío."""
    if not isinstance(valor, str) or not valor.strip():
        raise DatoInvalido(f"El campo '{campo}' es obligatorio.")
    return valor.strip()


def de_tipo[T](valor: object, tipo: type[T], campo: str) -> T:
    """Falla si ``valor`` no es del tipo esperado (p. ej. un Enum del dominio)."""
    if not isinstance(valor, tipo):
        raise DatoInvalido(f"El campo '{campo}' debe ser {tipo.__name__}.")
    return valor
