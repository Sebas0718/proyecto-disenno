"""Pruebas del contrato CO-02 reservarMaquina (CU-15) y de CU-16 liberación."""

from datetime import datetime, timedelta

import pytest

from compulab.aplicacion.casos_uso.liberar_reservas import LiberarReservasNoPresentadas
from compulab.aplicacion.casos_uso.reservar_maquina import ReservarMaquina, ReservarMaquinaComando
from compulab.dominio.comun.errores import (
    EnElPasado,
    IntervaloInvalido,
    LaboratorioCerrado,
    LimiteSemanalDeReservas,
    MaquinaFueraDeServicio,
    MaquinaOcupada,
    NoAutorizado,
    NoEncontrado,
    ReservaActivaExistente,
    ReservaMuyLarga,
)
from compulab.dominio.horario.turno import EstadoTurno
from compulab.dominio.reservas.reserva import EstadoReserva
from tests.dobles import Escenario, asistente, dia, en


@pytest.fixture
def esc() -> Escenario:
    escenario = Escenario()
    escenario.con_asistente(asistente("A1"))
    escenario.con_asistente(asistente("A2"))
    # El LAB-1 abre lunes y martes de 8 a 12 y de 12 a 16 (dos turnos seguidos).
    for d in (0, 1):
        escenario.con_turno(en(dia(d), 8, 12), asistente_id="A1")
        escenario.con_turno(en(dia(d), 12, 16), asistente_id="A2")
    return escenario


def reservar(esc: Escenario, inicio: datetime, fin: datetime, **cambios):
    datos = dict(solicitante_id="E1", maquina_id="M-LAB-1-1", inicio=inicio, fin=fin)
    datos.update(cambios)
    caso = ReservarMaquina(esc.fabrica, esc.directorio, esc.reloj)
    return caso.ejecutar(ReservarMaquinaComando(**datos))


def franja(d: int, desde: int, hasta: int) -> tuple[datetime, datetime]:
    intervalo = en(dia(d), desde, hasta)
    return intervalo.inicio, intervalo.fin


# --- Poscondiciones ---------------------------------------------------------------


def test_pc1_se_crea_una_instancia_de_reserva(esc):
    resultado = reservar(esc, *franja(0, 9, 11))
    assert resultado.reserva_id in esc.almacen.reservas


def test_pc2_la_reserva_queda_asociada_al_estudiante_maquina_y_franja(esc):
    resultado = reservar(esc, *franja(0, 9, 11))
    reserva = esc.almacen.reservas[resultado.reserva_id]
    assert reserva.estudiante_id == "E1"
    assert reserva.maquina_id == "M-LAB-1-1"
    assert reserva.intervalo == en(dia(0), 9, 11)


def test_pc3_la_reserva_queda_activa(esc):
    assert reservar(esc, *franja(0, 9, 11)).estado is EstadoReserva.ACTIVA


def test_pc4_el_limite_de_llegada_es_el_inicio_mas_15_minutos(esc):
    inicio, fin = franja(0, 9, 11)
    assert reservar(esc, inicio, fin).limite_de_llegada == inicio + timedelta(minutes=15)


def test_pc5_la_reserva_queda_persistida_y_ocupa_la_maquina(esc):
    reservar(esc, *franja(0, 9, 11))
    with pytest.raises(MaquinaOcupada):
        reservar(esc, *franja(0, 10, 12), solicitante_id="E2")


def test_dos_turnos_seguidos_cubren_una_reserva_que_cruza_de_uno_a_otro(esc):
    assert reservar(esc, *franja(0, 11, 13)).estado is EstadoReserva.ACTIVA


# --- Extensiones --------------------------------------------------------------------


def test_ext_4a_solo_los_estudiantes_reservan(esc):
    with pytest.raises(NoAutorizado):
        reservar(esc, *franja(0, 9, 11), solicitante_id="CL1")


def test_ext_5a_maquina_inexistente(esc):
    with pytest.raises(NoEncontrado):
        reservar(esc, *franja(0, 9, 11), maquina_id="M-NO-EXISTE")


def test_ext_5b_maquina_fuera_de_servicio(esc):
    with pytest.raises(MaquinaFueraDeServicio):
        reservar(esc, *franja(0, 9, 11), maquina_id="M-ROTA")


def test_ext_6a_fin_no_posterior_al_inicio(esc):
    inicio, _ = franja(0, 9, 11)
    with pytest.raises(IntervaloInvalido):
        reservar(esc, inicio, inicio)


def test_ext_6b_mas_de_dos_horas(esc):
    inicio, _ = franja(0, 9, 11)
    with pytest.raises(ReservaMuyLarga):
        reservar(esc, inicio, inicio + timedelta(hours=2, minutes=1))
    assert esc.almacen.reservas == {}


def test_ext_6c_franja_en_el_pasado(esc):
    esc.reloj.momento = en(dia(0), 10, 11).inicio
    with pytest.raises(EnElPasado):
        reservar(esc, *franja(0, 9, 11))


def test_ext_7a_laboratorio_cerrado_sin_turno(esc):
    with pytest.raises(LaboratorioCerrado):
        reservar(esc, *franja(2, 9, 11))  # miércoles: no hay turnos


def test_ext_7a_laboratorio_cerrado_en_parte_de_la_franja(esc):
    with pytest.raises(LaboratorioCerrado):
        reservar(esc, *franja(0, 15, 17))  # cierra a las 16


def test_ext_7a_un_turno_pendiente_no_abre_el_laboratorio(esc):
    esc.con_turno(en(dia(2), 8, 12), estado=EstadoTurno.PENDIENTE_ACEPTACION)
    with pytest.raises(LaboratorioCerrado):
        reservar(esc, *franja(2, 9, 11))


def test_ext_8a_maquina_ocupada_en_esa_franja(esc):
    esc.con_reserva(en(dia(0), 10, 12), estudiante_id="E2")
    with pytest.raises(MaquinaOcupada, match="10:00"):
        reservar(esc, *franja(0, 9, 11))


def test_ext_8a_otra_maquina_del_mismo_laboratorio_si_esta_libre(esc):
    esc.con_reserva(en(dia(0), 10, 12), estudiante_id="E2")
    assert reservar(esc, *franja(0, 9, 11), maquina_id="M-LAB-1-2").reserva_id


def test_ext_9a_ya_tiene_una_reserva_activa(esc):
    esc.con_reserva(en(dia(1), 9, 10), maquina_id="M-LAB-1-2")
    with pytest.raises(ReservaActivaExistente):
        reservar(esc, *franja(0, 13, 14))


def test_ext_10a_mas_de_seis_horas_en_la_semana(esc):
    # Ya terminaron (no están activas) pero suman 5 h esta semana.
    esc.reloj.momento = en(dia(1), 8, 9).inicio
    esc.con_reserva(en(dia(0), 8, 10), estado=EstadoReserva.EN_USO)
    esc.con_reserva(en(dia(0), 10, 12), estado=EstadoReserva.EN_USO, maquina_id="M-LAB-1-2")
    esc.con_reserva(en(dia(0), 13, 14), estado=EstadoReserva.LIBERADA)
    with pytest.raises(LimiteSemanalDeReservas, match="6 h"):
        reservar(esc, *franja(1, 9, 11))  # 7 h


def test_ext_10a_las_canceladas_no_cuentan_para_el_limite(esc):
    esc.reloj.momento = en(dia(1), 8, 9).inicio
    esc.con_reserva(en(dia(0), 8, 10), estado=EstadoReserva.CANCELADA)
    esc.con_reserva(en(dia(0), 10, 12), estado=EstadoReserva.EN_USO, maquina_id="M-LAB-1-2")
    esc.con_reserva(en(dia(0), 12, 14), estado=EstadoReserva.EN_USO)
    assert reservar(esc, *franja(1, 9, 11)).reserva_id  # 4 + 2 = 6 h


def test_ext_11a_si_no_se_presenta_en_15_minutos_se_libera_y_la_maquina_queda_libre(esc):
    inicio, fin = franja(0, 9, 11)
    reserva_id = reservar(esc, inicio, fin).reserva_id

    esc.reloj.momento = inicio + timedelta(minutes=14)
    liberar = LiberarReservasNoPresentadas(esc.fabrica, esc.reloj)
    assert liberar.ejecutar() == 0

    esc.reloj.momento = inicio + timedelta(minutes=15)
    assert liberar.ejecutar() == 1
    assert esc.almacen.reservas[reserva_id].estado is EstadoReserva.LIBERADA
    # La máquina vuelve a estar disponible para quien llegue.
    assert reservar(esc, inicio + timedelta(minutes=20), fin, solicitante_id="E2").reserva_id
