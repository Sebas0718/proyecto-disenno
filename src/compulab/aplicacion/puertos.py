"""Puertos: lo que la aplicación necesita del mundo exterior, como interfaces.

Cada puerto es un ``typing.Protocol``: describe *qué* se necesita sin decir
*cómo* se hace. Los adaptadores de ``compulab.infraestructura`` los
implementan (PostgreSQL, memoria, CSV, reloj del sistema...) y la raíz de
composición (``compulab.api.composicion``) decide cuál se inyecta. En las
pruebas se inyectan dobles (tests/dobles.py).

Protocol usa *tipado estructural*: un adaptador no hereda del puerto, basta
con que tenga los mismos métodos. Así la infraestructura no depende de
herencias raras y un doble de prueba es una clase de cinco líneas.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self

from compulab.dominio.comun.tiempo import IntervaloTiempo, Mes
from compulab.dominio.comun.usuario import Usuario
from compulab.dominio.horario.asistente import Asistente
from compulab.dominio.horario.turno import Turno
from compulab.dominio.pagos.asistencia import Asistencia
from compulab.dominio.pagos.cierre import CierreMensual
from compulab.dominio.pagos.tarifario import Tarifario
from compulab.dominio.reservas.laboratorio import Laboratorio, Maquina
from compulab.dominio.reservas.reserva import Reserva

# --- Servicios externos ----------------------------------------------------------


class Reloj(Protocol):
    """La hora actual. El dominio nunca la consulta; se la pasa la aplicación."""

    def ahora(self) -> datetime: ...


class Notificador(Protocol):
    """Avisos a personas (correo, push...). Hoy el adaptador solo registra."""

    def notificar(self, destinatario_id: str, asunto: str, mensaje: str) -> None: ...


class DirectorioInstitucional(Protocol):
    """El directorio del Centro de Cómputo: dice quién es quién."""

    def buscar(self, usuario_id: str) -> Usuario | None: ...

    def listar(self) -> list[Usuario]: ...


class ExportadorPlanilla(Protocol):
    """Genera el archivo que Becas acepta y devuelve dónde quedó."""

    def exportar(self, cierre: CierreMensual) -> str: ...


# --- Repositorios ------------------------------------------------------------------


class RepositorioLaboratorios(Protocol):
    def obtener(self, laboratorio_id: str) -> Laboratorio | None: ...

    def listar(self) -> list[Laboratorio]: ...

    def agregar(self, laboratorio: Laboratorio) -> None: ...


class RepositorioMaquinas(Protocol):
    def obtener(self, maquina_id: str) -> Maquina | None: ...

    def del_laboratorio(self, laboratorio_id: str) -> list[Maquina]: ...

    def agregar(self, maquina: Maquina) -> None: ...


class RepositorioAsistentes(Protocol):
    def obtener(self, asistente_id: str, *, bloquear: bool = False) -> Asistente | None:
        """Con ``bloquear=True`` nadie más puede modificar al asistente hasta que
        termine la unidad de trabajo (evita que dos coordinadores le asignen
        turnos al mismo tiempo y juntos superen su tope; ADR-0005)."""
        ...

    def listar(self) -> list[Asistente]: ...

    def agregar(self, asistente: Asistente) -> None: ...


class RepositorioTurnos(Protocol):
    def siguiente_id(self) -> str: ...

    def obtener(self, turno_id: str) -> Turno | None: ...

    def agregar(self, turno: Turno) -> None: ...

    def actualizar(self, turno: Turno) -> None: ...

    def del_asistente_en(self, asistente_id: str, periodo: IntervaloTiempo) -> list[Turno]:
        """Turnos del asistente (en cualquier laboratorio) que tocan el periodo."""
        ...

    def del_laboratorio_en(self, laboratorio_id: str, periodo: IntervaloTiempo) -> list[Turno]: ...

    def pendientes_del_asistente(self, asistente_id: str) -> list[Turno]: ...


class RepositorioReservas(Protocol):
    def siguiente_id(self) -> str: ...

    def agregar(self, reserva: Reserva) -> None: ...

    def actualizar(self, reserva: Reserva) -> None: ...

    def de_maquina_en(self, maquina_id: str, periodo: IntervaloTiempo) -> list[Reserva]: ...

    def del_estudiante_en(self, estudiante_id: str, periodo: IntervaloTiempo) -> list[Reserva]: ...

    def activas_del_estudiante(self, estudiante_id: str, ahora: datetime) -> list[Reserva]: ...

    def sin_presentarse(self, ahora: datetime) -> list[Reserva]:
        """Reservas ACTIVAS cuyo plazo de llegada de 15 minutos ya venció."""
        ...


class RepositorioAsistencias(Protocol):
    def en(self, periodo: IntervaloTiempo) -> list[Asistencia]:
        """Asistencias cuya entrada cae dentro del periodo."""
        ...

    def agregar(self, asistencia: Asistencia) -> None: ...


class RepositorioTarifarios(Protocol):
    def todos(self) -> list[Tarifario]: ...

    def agregar(self, tarifario: Tarifario) -> None: ...


class RepositorioCierres(Protocol):
    def existe(self, mes: Mes) -> bool: ...

    def agregar(self, cierre: CierreMensual) -> None: ...

    def obtener(self, mes: Mes) -> CierreMensual | None: ...

    def listar(self) -> list[CierreMensual]: ...


# --- Unidad de trabajo ---------------------------------------------------------------


class UnidadDeTrabajo(Protocol):
    """Agrupa los repositorios bajo una sola transacción (patrón Unit of Work).

    Uso::

        with fabrica_uow() as uow:
            ...cambios...
            uow.confirmar()   # si no se llama, todo se revierte al salir

    Si ocurre un error antes de ``confirmar()``, nada queda guardado: por
    ejemplo, si falla la generación del archivo de Becas, el mes no queda
    cerrado a medias.
    """

    laboratorios: RepositorioLaboratorios
    maquinas: RepositorioMaquinas
    asistentes: RepositorioAsistentes
    turnos: RepositorioTurnos
    reservas: RepositorioReservas
    asistencias: RepositorioAsistencias
    tarifarios: RepositorioTarifarios
    cierres: RepositorioCierres

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None: ...

    def confirmar(self) -> None: ...


FabricaDeUnidadDeTrabajo = Callable[[], UnidadDeTrabajo]
"""Cada ejecución de un caso de uso abre su propia unidad de trabajo."""
