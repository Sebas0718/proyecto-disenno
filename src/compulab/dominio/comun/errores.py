"""Errores del dominio.

Cada regla del enunciado que se puede romper tiene su propio error y su propio
código (``E-...``). Los códigos son los que aparecen en las extensiones de los
casos de uso (docs/02-casos-de-uso.md), así que este archivo sirve también de
índice: si una extensión no tiene error aquí, falta implementarla.

Jerarquía:
    ErrorDeDominio
    ├── NoAutorizado            -> el solicitante no tiene permiso
    ├── NoEncontrado            -> lo pedido no existe
    ├── DatoInvalido            -> se rompió una invariante de un objeto
    │   └── IntervaloInvalido
    └── ReglaDeNegocioViolada   -> los datos son válidos, pero la regla lo impide
        └── (una subclase por regla)
"""


class ErrorDeDominio(Exception):
    """Base de todos los errores del dominio."""

    codigo = "E-DOMINIO"

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoAutorizado(ErrorDeDominio):
    codigo = "E-NO-AUTORIZADO"


class NoEncontrado(ErrorDeDominio):
    codigo = "E-NO-ENCONTRADO"


class DatoInvalido(ErrorDeDominio):
    codigo = "E-DATO-INVALIDO"


class IntervaloInvalido(DatoInvalido):
    codigo = "E-INTERVALO-INVALIDO"


class ReglaDeNegocioViolada(ErrorDeDominio):
    codigo = "E-REGLA"


class TransicionInvalida(ReglaDeNegocioViolada):
    """Se pidió un cambio de estado que la máquina de estados no permite."""

    codigo = "E-TRANSICION-INVALIDA"


class EnElPasado(ReglaDeNegocioViolada):
    codigo = "E-EN-EL-PASADO"


# --- Horario -------------------------------------------------------------------


class AsistenteInactivo(ReglaDeNegocioViolada):
    codigo = "E-ASISTENTE-INACTIVO"


class TraslapeDeTurno(ReglaDeNegocioViolada):
    codigo = "E-TRASLAPE"


class TopeSemanalExcedido(ReglaDeNegocioViolada):
    codigo = "E-TOPE-SEMANAL"


class LaboratorioYaCubierto(ReglaDeNegocioViolada):
    """Un turno tiene exactamente un responsable: no hay dos turnos simultáneos en un lab."""

    codigo = "E-LABORATORIO-CUBIERTO"


# --- Reservas ------------------------------------------------------------------


class MaquinaFueraDeServicio(ReglaDeNegocioViolada):
    codigo = "E-MAQUINA-FUERA-DE-SERVICIO"


class ReservaMuyLarga(ReglaDeNegocioViolada):
    codigo = "E-RESERVA-MUY-LARGA"


class LaboratorioCerrado(ReglaDeNegocioViolada):
    codigo = "E-LABORATORIO-CERRADO"


class MaquinaOcupada(ReglaDeNegocioViolada):
    codigo = "E-MAQUINA-OCUPADA"


class ReservaActivaExistente(ReglaDeNegocioViolada):
    codigo = "E-RESERVA-ACTIVA-EXISTENTE"


class LimiteSemanalDeReservas(ReglaDeNegocioViolada):
    codigo = "E-LIMITE-SEMANAL-RESERVAS"


# --- Pagos ---------------------------------------------------------------------


class MesNoTerminado(ReglaDeNegocioViolada):
    codigo = "E-MES-NO-TERMINADO"


class MesYaCerrado(ReglaDeNegocioViolada):
    codigo = "E-MES-YA-CERRADO"


class SinTarifarioVigente(ReglaDeNegocioViolada):
    codigo = "E-SIN-TARIFARIO"
