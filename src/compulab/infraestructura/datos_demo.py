"""Datos de demostración, generados *relativos a hoy*.

Así la demo funciona el día que se presente: siempre hay turnos esta semana
y la siguiente (para reservar y asignar) y asistencias del mes anterior (para
cerrarlo). Se cargan con los mismos repositorios que usa el sistema, tanto en
memoria como en PostgreSQL, así que hay una sola fuente de datos de ejemplo.

Patrón semanal de turnos (todos CONFIRMADOS):
  Lab 1: Pablo L/M/V 08-11 · Marco K/J 08-12 · Sofía L-V 13-15
  Lab 2: Jorge L-J 18-20 (nocturno: lleva recargo)
  Lab 3: Sofía sábado 08-10 (fin de semana: lleva recargo)
El sábado de la semana próxima hay un turno de Pablo PENDIENTE de aceptación.
Marco se queda una hora de más los jueves: trabaja 9 h con tope de 8, y esa
hora queda sin pagar en el cierre. Pablo no llegó el último viernes del mes
anterior: ese turno queda "no cubierto" y sin pago.
"""

from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal

from compulab.aplicacion.puertos import UnidadDeTrabajo
from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.tiempo import IntervaloTiempo, Mes, SemanaISO
from compulab.dominio.comun.usuario import Rol, Usuario
from compulab.dominio.horario.asistente import Asistente, Categoria, EstadoAsistente
from compulab.dominio.horario.disponibilidad import BloqueDisponible, DiaSemana, Disponibilidad
from compulab.dominio.horario.turno import EstadoTurno, Turno
from compulab.dominio.pagos.asistencia import Asistencia
from compulab.dominio.pagos.tarifario import Tarifario
from compulab.dominio.reservas.laboratorio import EstadoMaquina, Laboratorio, Maquina

L, K, M, J, V, S = (
    DiaSemana.LUNES,
    DiaSemana.MARTES,
    DiaSemana.MIERCOLES,
    DiaSemana.JUEVES,
    DiaSemana.VIERNES,
    DiaSemana.SABADO,
)
SEMANA_LABORAL = (L, K, M, J, V)
COORDINADOR_SOPORTE = "SOP-1"


def usuarios_demo() -> list[Usuario]:
    return [
        Usuario(COORDINADOR_SOPORTE, "Ana Solís", Rol.COORDINADOR_SOPORTE),
        Usuario("CL-1", "Luis Mora", Rol.COORDINADOR_LABORATORIO, "LAB-1"),
        Usuario("CL-2", "Carla Jiménez", Rol.COORDINADOR_LABORATORIO, "LAB-2"),
        Usuario("CL-3", "Diego Vargas", Rol.COORDINADOR_LABORATORIO, "LAB-3"),
        Usuario("CL-4", "Elena Castro", Rol.COORDINADOR_LABORATORIO, "LAB-4"),
        Usuario("A-01", "Pablo Rojas", Rol.ESTUDIANTE),
        Usuario("A-02", "Sofía Herrera", Rol.ESTUDIANTE),
        Usuario("A-03", "Marco Ulate", Rol.ESTUDIANTE),
        Usuario("A-04", "Valeria Núñez", Rol.ESTUDIANTE),
        Usuario("A-05", "Jorge Pérez", Rol.ESTUDIANTE),
        Usuario("E-01", "Andrés Quesada", Rol.ESTUDIANTE),
        Usuario("E-02", "Laura Campos", Rol.ESTUDIANTE),
    ]


def _bloques(dias: tuple[DiaSemana, ...], inicio: int, fin: int) -> list[BloqueDisponible]:
    return [BloqueDisponible(d, time(inicio), time(fin)) for d in dias]


def _asistentes() -> list[Asistente]:
    return [
        Asistente(
            "A-01", "Pablo Rojas", Categoria.A, Decimal(10),
            Disponibilidad(_bloques(SEMANA_LABORAL, 7, 13)),
        ),
        Asistente(
            "A-02", "Sofía Herrera", Categoria.B, Decimal(12),
            Disponibilidad(_bloques(SEMANA_LABORAL, 12, 21) + _bloques((S,), 8, 14)),
        ),
        Asistente(
            "A-03", "Marco Ulate", Categoria.A, Decimal(8),
            Disponibilidad(_bloques((K, J), 8, 20)),
        ),
        Asistente(
            "A-04", "Valeria Núñez", Categoria.B, Decimal(15),
            Disponibilidad(_bloques(SEMANA_LABORAL, 8, 17)), EstadoAsistente.RENUNCIO,
        ),
        Asistente(
            "A-05", "Jorge Pérez", Categoria.A, Decimal(10),
            Disponibilidad(_bloques(SEMANA_LABORAL, 7, 22)),
        ),
    ]  # fmt: skip


# (laboratorio, asistente, días, hora de inicio, hora de fin)
PATRON_SEMANAL = (
    ("LAB-1", "A-01", (L, M, V), 8, 11),
    ("LAB-1", "A-03", (K, J), 8, 12),
    ("LAB-1", "A-02", SEMANA_LABORAL, 13, 15),
    ("LAB-2", "A-05", (L, K, M, J), 18, 20),
    ("LAB-3", "A-02", (S,), 8, 10),
)


def cargar_datos_demo(uow: UnidadDeTrabajo, hoy: date) -> bool:
    """Carga los datos si el almacén está vacío. Devuelve True si cargó algo."""
    if uow.laboratorios.listar():
        return False

    laboratorios = [
        Laboratorio("LAB-1", "Laboratorio 1", "Campus Central Cartago"),
        Laboratorio("LAB-2", "Laboratorio 2", "Campus Central Cartago"),
        Laboratorio("LAB-3", "Laboratorio 3", "Centro Académico San José"),
        Laboratorio("LAB-4", "Laboratorio 4", "Centro Académico San José"),
    ]
    for numero, laboratorio in enumerate(laboratorios, start=1):
        uow.laboratorios.agregar(laboratorio)
        for m in range(1, 9):
            codigo = f"L{numero}-{m:02d}"
            estado = EstadoMaquina.FUERA_DE_SERVICIO if (numero, m) == (1, 8) else None
            uow.maquinas.agregar(
                Maquina(f"M-{codigo}", laboratorio.id, codigo, estado or EstadoMaquina.EN_SERVICIO)
            )

    for asistente in _asistentes():
        uow.asistentes.agregar(asistente)

    uow.tarifarios.agregar(
        Tarifario(
            "TAR-1",
            vigente_desde=date(hoy.year - 1, 1, 1),
            vigente_hasta=None,
            tarifas_por_hora={
                Categoria.A: Dinero(Decimal(2500)),
                Categoria.B: Dinero(Decimal(3000)),
            },
            porcentaje_recargo=Decimal(50),
        )
    )

    # Turnos desde la semana del día 1 del mes anterior hasta el fin de la semana próxima.
    mes_anterior = Mes.de(hoy.replace(day=1) - timedelta(days=1))
    desde = SemanaISO.de(mes_anterior.primer_dia).lunes
    hasta = SemanaISO.de(hoy).lunes + timedelta(days=14)
    ultimo_viernes = max(
        d for d in _dias(mes_anterior.primer_dia, hoy.replace(day=1)) if d.weekday() == V
    )
    contador = 0
    dia = desde
    while dia < hasta:
        for laboratorio_id, asistente_id, dias, inicio, fin in PATRON_SEMANAL:
            if dia.weekday() not in dias:
                continue
            contador += 1
            intervalo = IntervaloTiempo.en_dia(dia, time(inicio), time(fin))
            turno = Turno(
                f"TS-{contador}", laboratorio_id, asistente_id, intervalo,
                EstadoTurno.CONFIRMADO, "CL-1" if laboratorio_id == "LAB-1" else "SOP-1",
            )  # fmt: skip
            uow.turnos.agregar(turno)
            if dia >= hoy:
                continue
            if asistente_id == "A-01" and dia == ultimo_viernes:
                continue  # turno no cubierto: nadie marcó entrada
            entrada, salida = intervalo.inicio, intervalo.fin
            if asistente_id == "A-03" and dia.weekday() == J:
                salida += timedelta(hours=1)  # se quedó una hora de más
            if asistente_id == "A-01":
                entrada += timedelta(minutes=5)  # llegó 5 minutos tarde
            asistencia = Asistencia(
                f"AS-{contador}", turno.id, asistente_id, intervalo.inicio, entrada, salida
            )
            uow.asistencias.agregar(asistencia)
        dia += timedelta(days=1)

    # Un turno fuera de la disponibilidad de Pablo (no declaró sábados), esperando
    # su aceptación. Con él, Pablo llega justo a su tope de 10 h esa semana.
    sabado_proximo = SemanaISO.de(hoy).lunes + timedelta(days=7 + S)
    uow.turnos.agregar(
        Turno(
            "TS-PENDIENTE", "LAB-3", "A-01",
            IntervaloTiempo.en_dia(sabado_proximo, time(11), time(12)),
            EstadoTurno.PENDIENTE_ACEPTACION, "CL-3",
        )
    )  # fmt: skip
    return True


def _dias(desde: date, hasta: date) -> list[date]:
    return [desde + timedelta(days=n) for n in range((hasta - desde).days)]
