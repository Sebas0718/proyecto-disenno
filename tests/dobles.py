"""Dobles de prueba (test doubles) y un "escenario" para armar datos con poco código.

Tipos de doble que se usan (vocabulario de Meszaros):
- ``RelojFijo``            stub: siempre devuelve la misma hora.
- ``NotificadorEspia``     spy: guarda lo que se le pidió, para verificarlo.
- ``ExportadorEspia``      spy: guarda los cierres exportados; puede simular fallos.
- ``UnidadDeTrabajoEnMemoria`` (de infraestructura) fake: repositorio que funciona
  de verdad, pero en memoria.
Ninguno toca red, archivos, base de datos ni el reloj real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.comun.usuario import Rol, Usuario
from compulab.dominio.horario.asistente import Asistente, Categoria, EstadoAsistente
from compulab.dominio.horario.disponibilidad import BloqueDisponible, DiaSemana, Disponibilidad
from compulab.dominio.horario.turno import EstadoTurno, Turno
from compulab.dominio.pagos.asistencia import Asistencia
from compulab.dominio.pagos.cierre import CierreMensual
from compulab.dominio.pagos.tarifario import Tarifario
from compulab.dominio.reservas.laboratorio import EstadoMaquina, Laboratorio, Maquina
from compulab.dominio.reservas.reserva import EstadoReserva, Reserva
from compulab.infraestructura.memoria import AlmacenEnMemoria, fabrica_en_memoria
from compulab.infraestructura.servicios import DirectorioEnMemoria

# Lunes 16 de noviembre de 2026 (semana ISO 2026-W47).
LUNES = date(2026, 11, 16)
AHORA = datetime(2026, 11, 13, 9, 0)  # viernes anterior: todo lo de la semana es futuro


def en(dia: date, hora_inicio: int, hora_fin: int) -> IntervaloTiempo:
    return IntervaloTiempo.en_dia(dia, time(hora_inicio), time(hora_fin))


def dia(offset: int) -> date:
    """Día relativo al LUNES de la semana de prueba (0 = lunes, 5 = sábado)."""
    return LUNES + timedelta(days=offset)


class RelojFijo:
    def __init__(self, ahora: datetime = AHORA) -> None:
        self.momento = ahora

    def ahora(self) -> datetime:
        return self.momento


@dataclass
class NotificadorEspia:
    enviados: list[tuple[str, str, str]] = field(default_factory=list)

    def notificar(self, destinatario_id: str, asunto: str, mensaje: str) -> None:
        self.enviados.append((destinatario_id, asunto, mensaje))

    def para(self, destinatario_id: str) -> list[tuple[str, str, str]]:
        return [e for e in self.enviados if e[0] == destinatario_id]


@dataclass
class ExportadorEspia:
    exportados: list[CierreMensual] = field(default_factory=list)
    fallar: bool = False

    def exportar(self, cierre: CierreMensual) -> str:
        if self.fallar:
            raise OSError("Disco lleno (simulado)")
        self.exportados.append(cierre)
        return f"memoria://becas-{cierre.mes}.csv"


SOPORTE = Usuario("SOP", "Ana Soporte", Rol.COORDINADOR_SOPORTE)
COORD_LAB1 = Usuario("CL1", "Luis Lab1", Rol.COORDINADOR_LABORATORIO, "LAB-1")
COORD_LAB2 = Usuario("CL2", "Carla Lab2", Rol.COORDINADOR_LABORATORIO, "LAB-2")
ESTUDIANTE = Usuario("E1", "Elena Estudiante", Rol.ESTUDIANTE)
OTRO_ESTUDIANTE = Usuario("E2", "Esteban Estudiante", Rol.ESTUDIANTE)
ASISTENTE_USUARIO = Usuario("A1", "Ana Asistente", Rol.ESTUDIANTE)


def asistente(
    id: str = "A1",
    tope: int = 10,
    categoria: Categoria = Categoria.A,
    estado: EstadoAsistente = EstadoAsistente.ACTIVO,
    nombre: str | None = None,
) -> Asistente:
    """Asistente disponible de lunes a viernes de 8:00 a 17:00."""
    bloques = [BloqueDisponible(DiaSemana(d), time(8), time(17)) for d in range(5)]
    return Asistente(
        id, nombre or f"Asistente {id}", categoria, Decimal(tope), Disponibilidad(bloques), estado
    )


def tarifario(desde: date = date(2026, 1, 1), recargo: int = 50) -> Tarifario:
    return Tarifario(
        "TAR",
        desde,
        None,
        {Categoria.A: Dinero(Decimal(1000)), Categoria.B: Dinero(Decimal(2000))},
        Decimal(recargo),
    )


class Escenario:
    """Almacén en memoria con dos laboratorios, máquinas y usuarios de prueba."""

    def __init__(self) -> None:
        self.almacen = AlmacenEnMemoria()
        self.fabrica = fabrica_en_memoria(self.almacen)
        self.reloj = RelojFijo()
        self.notificador = NotificadorEspia()
        self.exportador = ExportadorEspia()
        self.directorio = DirectorioEnMemoria(
            [SOPORTE, COORD_LAB1, COORD_LAB2, ESTUDIANTE, OTRO_ESTUDIANTE, ASISTENTE_USUARIO]
        )
        a = self.almacen
        a.laboratorios["LAB-1"] = Laboratorio("LAB-1", "Lab 1", "Cartago")
        a.laboratorios["LAB-2"] = Laboratorio("LAB-2", "Lab 2", "San José")
        for lab in ("LAB-1", "LAB-2"):
            for n in (1, 2):
                a.maquinas[f"M-{lab}-{n}"] = Maquina(f"M-{lab}-{n}", lab, f"{lab}-{n}")
        a.maquinas["M-ROTA"] = Maquina(
            "M-ROTA", "LAB-1", "LAB-1-R", EstadoMaquina.FUERA_DE_SERVICIO
        )

    # --- atajos para poblar el almacén --------------------------------------------
    def con_asistente(self, nuevo: Asistente) -> Asistente:
        self.almacen.asistentes[nuevo.id] = nuevo
        return nuevo

    def con_turno(
        self,
        intervalo: IntervaloTiempo,
        asistente_id: str = "A1",
        laboratorio_id: str = "LAB-1",
        estado: EstadoTurno = EstadoTurno.CONFIRMADO,
        id: str | None = None,
    ) -> Turno:
        turno = Turno(
            id or f"TX-{len(self.almacen.turnos) + 1}",
            laboratorio_id,
            asistente_id,
            intervalo,
            estado,
            "CL1",
        )
        self.almacen.turnos[turno.id] = turno
        return turno

    def con_reserva(
        self,
        intervalo: IntervaloTiempo,
        estudiante_id: str = "E1",
        maquina_id: str = "M-LAB-1-1",
        estado: EstadoReserva = EstadoReserva.ACTIVA,
    ) -> Reserva:
        reserva = Reserva(
            f"RX-{len(self.almacen.reservas) + 1}", estudiante_id, maquina_id, intervalo, estado
        )
        self.almacen.reservas[reserva.id] = reserva
        return reserva

    def con_asistencia(
        self,
        asistente_id: str,
        entrada: datetime,
        salida: datetime,
        inicio_programado: datetime | None = None,
    ) -> Asistencia:
        n = len(self.almacen.asistencias) + 1
        asistencia = Asistencia(
            f"AS-{n}", f"TA-{n}", asistente_id, inicio_programado or entrada, entrada, salida
        )
        self.almacen.asistencias[asistencia.id] = asistencia
        return asistencia

    def con_tarifario(self, nuevo: Tarifario) -> Tarifario:
        self.almacen.tarifarios[nuevo.id] = nuevo
        return nuevo
