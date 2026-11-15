"""Pruebas del contrato CO-01 asignarTurno (CU-07) y de CU-08 responder turno.

Nombres: ``test_pcN_...`` prueba la poscondición N del contrato;
``test_ext_XX_...`` prueba la extensión XX del caso de uso (docs/02-casos-de-uso.md).
Todas usan dobles: almacén en memoria, reloj fijo y notificador espía.
"""

from datetime import time

import pytest

from compulab.aplicacion.casos_uso.asignar_turno import AsignarTurno, AsignarTurnoComando
from compulab.aplicacion.casos_uso.responder_turno import (
    ResponderTurnoComando,
    ResponderTurnoPendiente,
)
from compulab.dominio.comun.errores import (
    AsistenteInactivo,
    EnElPasado,
    IntervaloInvalido,
    LaboratorioYaCubierto,
    NoAutorizado,
    NoEncontrado,
    TopeSemanalExcedido,
    TransicionInvalida,
    TraslapeDeTurno,
)
from compulab.dominio.horario.asistente import EstadoAsistente
from compulab.dominio.horario.turno import EstadoTurno
from tests.dobles import Escenario, asistente, dia, en


@pytest.fixture
def esc() -> Escenario:
    escenario = Escenario()
    escenario.con_asistente(asistente("A1", tope=10))
    return escenario


def asignar(esc: Escenario, **cambios) -> object:
    datos = dict(
        solicitante_id="CL1",
        laboratorio_id="LAB-1",
        asistente_id="A1",
        dia=dia(0),
        hora_inicio=time(8),
        hora_fin=time(12),
    )
    datos.update(cambios)
    caso = AsignarTurno(esc.fabrica, esc.directorio, esc.reloj, esc.notificador)
    return caso.ejecutar(AsignarTurnoComando(**datos))


def responder(esc: Escenario, turno_id: str, acepta: bool, solicitante: str = "A1"):
    caso = ResponderTurnoPendiente(esc.fabrica, esc.directorio, esc.notificador)
    return caso.ejecutar(ResponderTurnoComando(solicitante, turno_id, acepta))


# --- Poscondiciones -------------------------------------------------------------


def test_pc1_se_crea_una_instancia_de_turno(esc):
    resultado = asignar(esc)
    assert resultado.turno_id in esc.almacen.turnos


def test_pc2_el_turno_queda_asociado_a_laboratorio_asistente_dia_horas_y_coordinador(esc):
    resultado = asignar(esc, dia=dia(1), hora_inicio=time(9), hora_fin=time(11))
    turno = esc.almacen.turnos[resultado.turno_id]
    assert turno.laboratorio_id == "LAB-1"
    assert turno.asistente_id == "A1"
    assert turno.intervalo == en(dia(1), 9, 11)
    assert turno.asignado_por == "CL1"


def test_pc3_bloque_declarado_queda_confirmado(esc):
    resultado = asignar(esc)
    assert resultado.estado is EstadoTurno.CONFIRMADO
    assert not resultado.requiere_aceptacion
    assert esc.notificador.enviados == []


def test_pc4_bloque_no_declarado_queda_pendiente_y_se_avisa_al_asistente(esc):
    resultado = asignar(esc, dia=dia(5), hora_inicio=time(9), hora_fin=time(11))  # sábado
    assert esc.almacen.turnos[resultado.turno_id].estado is EstadoTurno.PENDIENTE_ACEPTACION
    assert len(esc.notificador.para("A1")) == 1


def test_pc5_el_turno_queda_persistido_y_cuenta_para_las_siguientes_asignaciones(esc):
    asignar(esc, hora_inicio=time(8), hora_fin=time(12))
    with pytest.raises(TraslapeDeTurno):
        asignar(esc, laboratorio_id="LAB-2", solicitante_id="SOP", hora_inicio=time(11))


# --- Extensiones ---------------------------------------------------------------------


def test_ext_4a_laboratorio_inexistente(esc):
    with pytest.raises(NoEncontrado):
        asignar(esc, laboratorio_id="LAB-99")


def test_ext_4b_coordinador_de_otro_laboratorio_no_puede_asignar(esc):
    with pytest.raises(NoAutorizado):
        asignar(esc, solicitante_id="CL2")
    assert esc.almacen.turnos == {}


def test_ext_4b_el_coordinador_de_soporte_puede_asignar_en_cualquier_laboratorio(esc):
    resultado = asignar(esc, solicitante_id="SOP", laboratorio_id="LAB-2")
    assert esc.almacen.turnos[resultado.turno_id].laboratorio_id == "LAB-2"


def test_ext_4b_un_estudiante_no_puede_asignar(esc):
    with pytest.raises(NoAutorizado):
        asignar(esc, solicitante_id="E1")


def test_ext_5a_hora_de_fin_no_posterior_al_inicio(esc):
    with pytest.raises(IntervaloInvalido):
        asignar(esc, hora_inicio=time(12), hora_fin=time(12))


def test_ext_6a_asistente_inexistente(esc):
    with pytest.raises(NoEncontrado):
        asignar(esc, asistente_id="NADIE")


def test_ext_6b_turno_en_el_pasado(esc):
    esc.reloj.momento = en(dia(0), 9, 10).inicio  # ya empezó el turno de las 8
    with pytest.raises(EnElPasado):
        asignar(esc)


@pytest.mark.parametrize("estado", [EstadoAsistente.RENUNCIO, EstadoAsistente.DADO_DE_BAJA])
def test_ext_6c_asistente_inactivo(esc, estado):
    esc.con_asistente(asistente("A2", estado=estado))
    with pytest.raises(AsistenteInactivo):
        asignar(esc, asistente_id="A2")
    assert esc.almacen.turnos == {}


def test_ext_7a_traslape_aunque_sea_en_otro_laboratorio_y_campus(esc):
    esc.con_turno(en(dia(0), 10, 14), laboratorio_id="LAB-2")
    with pytest.raises(TraslapeDeTurno, match="LAB-2"):
        asignar(esc, hora_inicio=time(8), hora_fin=time(11))


def test_ext_7a_turnos_seguidos_no_se_traslapan(esc):
    esc.con_turno(en(dia(0), 12, 14), laboratorio_id="LAB-2")
    assert asignar(esc, hora_inicio=time(8), hora_fin=time(12)).estado is EstadoTurno.CONFIRMADO


def test_ext_7a_un_turno_rechazado_no_cuenta_como_traslape(esc):
    esc.con_turno(en(dia(0), 8, 12), estado=EstadoTurno.RECHAZADO, laboratorio_id="LAB-2")
    assert asignar(esc).estado is EstadoTurno.CONFIRMADO


def test_ext_7b_el_laboratorio_ya_tiene_responsable_en_esa_franja(esc):
    esc.con_asistente(asistente("A2"))
    esc.con_turno(en(dia(0), 10, 14), asistente_id="A2")
    with pytest.raises(LaboratorioYaCubierto):
        asignar(esc, hora_inicio=time(8), hora_fin=time(11))


def test_ext_8a_supera_el_tope_semanal_sumando_todos_los_laboratorios(esc):
    esc.con_turno(en(dia(1), 8, 12), laboratorio_id="LAB-1")
    esc.con_turno(en(dia(2), 8, 12), laboratorio_id="LAB-2")  # 8 h de 10
    with pytest.raises(TopeSemanalExcedido, match="10 h"):
        asignar(esc, dia=dia(3), hora_inicio=time(8), hora_fin=time(11))  # 11 h
    assert len(esc.almacen.turnos) == 2


def test_ext_8a_llegar_exactamente_al_tope_si_se_permite(esc):
    esc.con_turno(en(dia(1), 8, 16))  # 8 h de 10
    assert asignar(esc, dia=dia(3), hora_inicio=time(8), hora_fin=time(10)).turno_id


def test_ext_8a_los_turnos_de_otra_semana_no_cuentan(esc):
    esc.con_turno(en(dia(-3), 8, 17))  # viernes de la semana anterior, 9 h
    assert asignar(esc).estado is EstadoTurno.CONFIRMADO


def test_ext_9a_fuera_de_disponibilidad_queda_pendiente(esc):
    resultado = asignar(esc, hora_inicio=time(16), hora_fin=time(18))  # declaró hasta las 17
    assert resultado.requiere_aceptacion


def test_ext_9a1_el_asistente_acepta_y_queda_confirmado(esc):
    pendiente = esc.con_turno(en(dia(5), 9, 11), estado=EstadoTurno.PENDIENTE_ACEPTACION)
    assert responder(esc, pendiente.id, acepta=True) is EstadoTurno.CONFIRMADO
    assert esc.almacen.turnos[pendiente.id].confirmado


def test_ext_9a2_el_asistente_rechaza_y_se_avisa_al_coordinador(esc):
    pendiente = esc.con_turno(en(dia(5), 9, 11), estado=EstadoTurno.PENDIENTE_ACEPTACION)
    assert responder(esc, pendiente.id, acepta=False) is EstadoTurno.RECHAZADO
    assert len(esc.notificador.para("CL1")) == 1
    # El bloque vuelve a quedar libre para el asistente.
    asignar(esc, dia=dia(5), hora_inicio=time(9), hora_fin=time(11))


def test_ext_9a3_solo_el_asistente_del_turno_puede_responder(esc):
    pendiente = esc.con_turno(en(dia(5), 9, 11), estado=EstadoTurno.PENDIENTE_ACEPTACION)
    with pytest.raises(NoAutorizado):
        responder(esc, pendiente.id, acepta=True, solicitante="E1")
    assert esc.almacen.turnos[pendiente.id].estado is EstadoTurno.PENDIENTE_ACEPTACION


def test_ext_9a4_no_se_responde_un_turno_que_no_esta_pendiente(esc):
    confirmado = esc.con_turno(en(dia(0), 8, 10))
    with pytest.raises(TransicionInvalida):
        responder(esc, confirmado.id, acepta=False)


# --- Precondición ----------------------------------------------------------------------


def test_precondicion_solicitante_desconocido_en_el_directorio(esc):
    with pytest.raises(NoAutorizado):
        asignar(esc, solicitante_id="INTRUSO")
