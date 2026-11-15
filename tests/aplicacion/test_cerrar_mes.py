"""Pruebas del contrato CO-03 cerrarMes (CU-19).

Datos: tarifa A = ₡1000/h, B = ₡2000/h, recargo 50 %. Octubre 2026:
el 1 de octubre es jueves; la semana ISO 2026-W40 va del lunes 28/09 al 04/10.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from compulab.aplicacion.casos_uso.cerrar_mes import CerrarMes, CerrarMesComando
from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.errores import (
    MesNoTerminado,
    MesYaCerrado,
    NoAutorizado,
    SinTarifarioVigente,
)
from compulab.dominio.comun.tiempo import Mes
from compulab.dominio.horario.asistente import Categoria
from compulab.dominio.pagos.tarifario import Tarifario
from compulab.infraestructura.exportador_csv import contenido_csv
from tests.dobles import Escenario, asistente, tarifario

OCTUBRE = Mes(2026, 10)
NOVIEMBRE_1 = datetime(2026, 11, 1, 6, 0)


def h(fecha: date, hora: int, minuto: int = 0) -> datetime:
    return datetime(fecha.year, fecha.month, fecha.day, hora, minuto)


@pytest.fixture
def esc() -> Escenario:
    escenario = Escenario()
    escenario.reloj.momento = NOVIEMBRE_1
    escenario.con_tarifario(tarifario())
    escenario.con_asistente(asistente("A1", tope=10, categoria=Categoria.A, nombre="Ana"))
    escenario.con_asistente(asistente("A2", tope=10, categoria=Categoria.B, nombre="Beto"))
    return escenario


def cerrar(esc: Escenario, solicitante: str = "SOP", anio: int = 2026, mes: int = 10):
    caso = CerrarMes(esc.fabrica, esc.directorio, esc.reloj, esc.notificador, esc.exportador)
    return caso.ejecutar(CerrarMesComando(solicitante, anio, mes))


def trabajo(esc: Escenario, asistente_id: str, fecha: date, desde: int, hasta: int, **kw):
    return esc.con_asistencia(asistente_id, h(fecha, desde), h(fecha, hasta), **kw)


MARTES_6 = date(2026, 10, 6)


# --- Poscondiciones ---------------------------------------------------------------------


def test_pc1_se_crea_el_cierre_del_mes_con_la_fecha_de_cierre(esc):
    resultado = cerrar(esc)
    assert resultado.cierre.mes == OCTUBRE
    assert resultado.cierre.cerrado_en == NOVIEMBRE_1


def test_pc2_una_liquidacion_por_asistente_que_trabajo_en_el_mes(esc):
    trabajo(esc, "A1", MARTES_6, 8, 12)
    trabajo(esc, "A1", MARTES_6 + timedelta(days=1), 8, 10)
    trabajo(esc, "A2", date(2026, 11, 3), 8, 10)  # noviembre: no entra
    liquidaciones = cerrar(esc).cierre.liquidaciones
    assert [li.asistente_id for li in liquidaciones] == ["A1"]
    assert liquidaciones[0].horas_base == Decimal("6.00")


def test_pc3_las_horas_de_turnos_nocturnos_o_de_fin_de_semana_llevan_recargo(esc):
    trabajo(esc, "A1", MARTES_6, 17, 19)  # empieza 17:00: sin recargo aunque termine 19:00
    trabajo(esc, "A1", MARTES_6 + timedelta(days=1), 18, 20)  # nocturno
    trabajo(esc, "A1", date(2026, 10, 10), 9, 10)  # sábado
    li = cerrar(esc).cierre.liquidaciones[0]
    assert li.horas_base == Decimal("2.00")
    assert li.horas_con_recargo == Decimal("3.00")


def test_pc3_el_recargo_se_aplica_una_sola_vez_si_es_sabado_en_la_noche(esc):
    trabajo(esc, "A1", date(2026, 10, 10), 18, 20)
    li = cerrar(esc).cierre.liquidaciones[0]
    assert li.monto == Dinero(Decimal("3000.00"))  # 2 h × 1000 × 1,5 (no × 2,25)


def test_pc3_el_recargo_depende_del_inicio_programado_no_de_la_llegada(esc):
    trabajo(esc, "A1", MARTES_6, 18, 20, inicio_programado=h(MARTES_6, 17))
    li = cerrar(esc).cierre.liquidaciones[0]
    assert li.horas_con_recargo == 0
    assert li.horas_base == Decimal("2.00")


def test_pc4_las_horas_sobre_el_tope_semanal_quedan_sin_pagar_y_son_las_ultimas(esc):
    trabajo(esc, "A1", MARTES_6, 8, 14)  # 6 h base
    trabajo(esc, "A1", MARTES_6 + timedelta(days=2), 18, 23)  # 5 h nocturnas: 4 pagadas, 1 no
    li = cerrar(esc).cierre.liquidaciones[0]
    assert (li.horas_base, li.horas_con_recargo, li.horas_no_pagadas) == (
        Decimal("6.00"),
        Decimal("4.00"),
        Decimal("1.00"),
    )
    assert li.monto == Dinero(Decimal("12000.00"))  # 6×1000 + 4×1500


def test_pc4_las_horas_del_mes_anterior_en_la_misma_semana_cuentan_para_el_tope(esc):
    trabajo(esc, "A1", date(2026, 9, 29), 8, 16)  # martes de septiembre, misma semana ISO: 8 h
    trabajo(esc, "A1", date(2026, 10, 1), 8, 12)  # jueves 1 de octubre: 4 h, solo 2 caben
    li = cerrar(esc).cierre.liquidaciones[0]
    assert li.horas_base == Decimal("2.00")
    assert li.horas_no_pagadas == Decimal("2.00")


def test_pc5_el_monto_usa_la_tarifa_de_la_categoria_y_redondea_a_centimos(esc):
    esc.con_asistencia("A2", h(MARTES_6, 8), h(MARTES_6, 8, 20))  # 20 min de categoría B
    li = cerrar(esc).cierre.liquidaciones[0]
    assert li.monto == Dinero(Decimal("666.67"))  # 2000 × 20/60 = 666,666...


def test_pc5_si_el_tarifario_cambia_a_mitad_de_mes_cada_hora_usa_el_vigente(esc):
    esc.almacen.tarifarios.clear()
    esc.con_tarifario(
        Tarifario(
            "T1", date(2026, 1, 1), date(2026, 10, 14),
            {Categoria.A: Dinero(Decimal(1000)), Categoria.B: Dinero(Decimal(2000))}, Decimal(50),
        )
    )  # fmt: skip
    esc.con_tarifario(
        Tarifario(
            "T2", date(2026, 10, 15), None,
            {Categoria.A: Dinero(Decimal(1200)), Categoria.B: Dinero(Decimal(2400))}, Decimal(50),
        )
    )  # fmt: skip
    trabajo(esc, "A1", MARTES_6, 8, 10)  # 2 × 1000
    trabajo(esc, "A1", date(2026, 10, 20), 8, 10)  # 2 × 1200
    assert cerrar(esc).cierre.liquidaciones[0].monto == Dinero(Decimal("4400.00"))


def test_pc6_el_cierre_queda_registrado_y_el_mes_cerrado(esc):
    trabajo(esc, "A1", MARTES_6, 8, 10)
    cerrar(esc)
    assert OCTUBRE in esc.almacen.cierres
    assert esc.almacen.cierres[OCTUBRE].total == Dinero(Decimal("2000.00"))


def test_pc7_se_genera_el_archivo_para_becas_con_una_fila_por_liquidacion(esc):
    trabajo(esc, "A1", MARTES_6, 8, 10)
    trabajo(esc, "A2", MARTES_6, 10, 12)
    resultado = cerrar(esc)
    assert resultado.archivo == "memoria://becas-2026-10.csv"
    assert esc.exportador.exportados == [resultado.cierre]
    lineas = contenido_csv(resultado.cierre).splitlines()
    assert lineas[0].startswith("anio,mes,asistente_id")
    assert lineas[1:] == [
        "2026,10,A1,Ana,A,2.00,0.00,0.00,2000.00",
        "2026,10,A2,Beto,B,2.00,0.00,0.00,4000.00",
    ]


# --- Extensiones ----------------------------------------------------------------------------


@pytest.mark.parametrize("solicitante", ["CL1", "E1"])
def test_ext_2a_solo_el_coordinador_de_soporte_cierra_el_mes(esc, solicitante):
    with pytest.raises(NoAutorizado):
        cerrar(esc, solicitante=solicitante)


def test_ext_3a_el_mes_todavia_no_termino(esc):
    esc.reloj.momento = datetime(2026, 10, 31, 23, 59)
    with pytest.raises(MesNoTerminado):
        cerrar(esc)


def test_ext_3b_un_mes_cerrado_no_se_vuelve_a_calcular(esc):
    trabajo(esc, "A1", MARTES_6, 8, 10)
    primero = cerrar(esc).cierre
    trabajo(esc, "A1", MARTES_6 + timedelta(days=1), 8, 10)  # dato que llega tarde
    with pytest.raises(MesYaCerrado):
        cerrar(esc)
    assert esc.almacen.cierres[OCTUBRE].total == primero.total


def test_ext_4a_sin_asistencias_el_cierre_queda_vacio(esc):
    resultado = cerrar(esc)
    assert resultado.cierre.liquidaciones == ()
    assert contenido_csv(resultado.cierre).count("\n") == 1  # solo el encabezado


def test_ext_5a_horas_no_pagadas_se_avisan_al_coordinador_de_soporte(esc):
    trabajo(esc, "A1", MARTES_6, 8, 20)  # 12 h con tope 10
    cerrar(esc)
    avisos = esc.notificador.para("SOP")
    assert len(avisos) == 1
    assert "Ana: 2.00 h" in avisos[0][2]


def test_ext_5a_sin_horas_no_pagadas_no_hay_aviso(esc):
    trabajo(esc, "A1", MARTES_6, 8, 10)
    cerrar(esc)
    assert esc.notificador.enviados == []


def test_ext_5b_sin_tarifario_vigente_no_se_cierra(esc):
    esc.almacen.tarifarios.clear()
    esc.con_tarifario(tarifario(desde=date(2026, 10, 15)))
    trabajo(esc, "A1", MARTES_6, 8, 10)
    with pytest.raises(SinTarifarioVigente):
        cerrar(esc)
    assert esc.almacen.cierres == {}


def test_ext_7a_si_falla_el_archivo_el_mes_no_queda_cerrado(esc):
    trabajo(esc, "A1", MARTES_6, 8, 10)
    esc.exportador.fallar = True
    with pytest.raises(OSError):
        cerrar(esc)
    assert esc.almacen.cierres == {}
    esc.exportador.fallar = False
    assert cerrar(esc).cierre.mes == OCTUBRE  # se puede reintentar
