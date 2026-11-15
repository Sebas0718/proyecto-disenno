"""Los repositorios PostgreSQL guardan y leen lo mismo que el dominio espera, y
las restricciones de la base protegen las invariantes aunque se salte el dominio."""

from datetime import date, datetime, time

import psycopg
import pytest

from compulab.aplicacion.casos_uso.asignar_turno import AsignarTurno, AsignarTurnoComando
from compulab.aplicacion.casos_uso.cerrar_mes import CerrarMes, CerrarMesComando
from compulab.aplicacion.casos_uso.reservar_maquina import ReservarMaquina, ReservarMaquinaComando
from compulab.dominio.comun.errores import (
    LaboratorioYaCubierto,
    MaquinaOcupada,
    MesYaCerrado,
    TraslapeDeTurno,
)
from compulab.dominio.comun.tiempo import IntervaloTiempo, Mes
from compulab.dominio.horario.turno import EstadoTurno, Turno
from compulab.dominio.reservas.reserva import Reserva
from compulab.infraestructura.datos_demo import cargar_datos_demo, usuarios_demo
from compulab.infraestructura.servicios import DirectorioEnMemoria
from tests.dobles import ExportadorEspia, NotificadorEspia, RelojFijo

pytestmark = pytest.mark.integracion

HOY = date(2026, 11, 13)  # viernes
AHORA = datetime(2026, 11, 13, 7, 0)
LUNES = date(2026, 11, 16)


@pytest.fixture
def con_demo(fabrica):
    with fabrica() as uow:
        assert cargar_datos_demo(uow, HOY)
        uow.confirmar()
    return fabrica


def test_los_datos_se_leen_como_objetos_del_dominio(con_demo):
    with con_demo() as uow:
        asistente = uow.asistentes.obtener("A-02", bloquear=True)
        assert asistente is not None
        assert asistente.declaro_disponible(IntervaloTiempo.en_dia(LUNES, time(13), time(15)))
        assert len(uow.maquinas.del_laboratorio("LAB-1")) == 8
        assert len(uow.tarifarios.todos()) == 1


def test_caso_de_uso_asignar_turno_de_punta_a_punta(con_demo):
    caso = AsignarTurno(
        con_demo, DirectorioEnMemoria(usuarios_demo()), RelojFijo(AHORA), NotificadorEspia()
    )
    resultado = caso.ejecutar(
        AsignarTurnoComando("CL-1", "LAB-1", "A-05", date(2026, 11, 20), time(15), time(17))
    )
    with con_demo() as uow:
        assert uow.turnos.obtener(resultado.turno_id).estado is EstadoTurno.CONFIRMADO


def test_restriccion_de_traslape_aunque_se_salte_el_dominio(con_demo):
    with con_demo() as uow, pytest.raises(TraslapeDeTurno):
        uow.turnos.agregar(
            Turno(
                "T-X", "LAB-4", "A-02",
                IntervaloTiempo.en_dia(LUNES, time(14), time(16)),
                EstadoTurno.CONFIRMADO, "SOP-1",
            )
        )  # fmt: skip


def test_restriccion_de_un_responsable_por_laboratorio(con_demo):
    with con_demo() as uow, pytest.raises(LaboratorioYaCubierto):
        uow.turnos.agregar(
            Turno(
                "T-X", "LAB-1", "A-05",
                IntervaloTiempo.en_dia(LUNES, time(9), time(10)),
                EstadoTurno.CONFIRMADO, "SOP-1",
            )
        )  # fmt: skip


def test_reservar_y_restriccion_de_maquina_ocupada(con_demo):
    caso = ReservarMaquina(con_demo, DirectorioEnMemoria(usuarios_demo()), RelojFijo(AHORA))
    inicio, fin = datetime(2026, 11, 16, 9, 0), datetime(2026, 11, 16, 10, 30)
    caso.ejecutar(ReservarMaquinaComando("E-01", "M-L1-01", inicio, fin))
    with con_demo() as uow, pytest.raises(MaquinaOcupada):
        uow.reservas.agregar(Reserva("R-X", "E-02", "M-L1-01", IntervaloTiempo(inicio, fin)))


def test_cerrar_mes_y_el_cierre_es_inmutable_en_la_base(con_demo):
    caso = CerrarMes(
        con_demo,
        DirectorioEnMemoria(usuarios_demo()),
        RelojFijo(AHORA),
        NotificadorEspia(),
        ExportadorEspia(),
    )
    cierre = caso.ejecutar(CerrarMesComando("SOP-1", 2026, 10)).cierre
    with con_demo() as uow:
        guardado = uow.cierres.obtener(Mes(2026, 10))
        assert guardado is not None
        assert guardado.total == cierre.total
        assert {li.asistente_id for li in guardado.liquidaciones} == {
            "A-01",
            "A-02",
            "A-03",
            "A-05",
        }
    with pytest.raises(MesYaCerrado):
        caso.ejecutar(CerrarMesComando("SOP-1", 2026, 10))
    with con_demo() as uow, pytest.raises(psycopg.errors.IntegrityConstraintViolation):
        uow.cierres._c.execute("UPDATE liquidacion SET monto = 0")  # el trigger lo impide


def test_lo_no_confirmado_se_revierte(con_demo):
    with con_demo() as uow:
        uow.turnos.actualizar(
            Turno(
                "TS-PENDIENTE", "LAB-3", "A-01",
                IntervaloTiempo.en_dia(date(2026, 11, 21), time(11), time(12)),
                EstadoTurno.RECHAZADO, "CL-3",
            )
        )  # fmt: skip
        # sin confirmar()
    with con_demo() as uow:
        assert uow.turnos.obtener("TS-PENDIENTE").estado is EstadoTurno.PENDIENTE_ACEPTACION
