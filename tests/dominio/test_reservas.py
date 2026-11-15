"""Invariantes de Máquina y Reserva, y sus máquinas de estado."""

from datetime import timedelta

import pytest

from compulab.dominio.comun.errores import DatoInvalido, ReservaMuyLarga, TransicionInvalida
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.reservas.laboratorio import Laboratorio, Maquina
from compulab.dominio.reservas.reserva import EstadoReserva, Reserva
from tests.dobles import dia, en


def reserva(intervalo: IntervaloTiempo | None = None) -> Reserva:
    return Reserva("R", "E1", "M1", intervalo or en(dia(0), 9, 11))


class TestReserva:
    def test_exactamente_dos_horas_se_permite(self):
        assert reserva(en(dia(0), 9, 11)).intervalo.minutos == 120

    def test_mas_de_dos_horas_no(self):
        with pytest.raises(ReservaMuyLarga):
            reserva(en(dia(0), 9, 12))

    def test_no_cruza_la_medianoche(self):
        inicio = en(dia(0), 22, 23).fin  # 23:00; una hora después ya es otro día
        with pytest.raises(DatoInvalido):
            reserva(IntervaloTiempo(inicio, inicio + timedelta(hours=1)))

    def test_llegada_dentro_de_los_15_minutos(self):
        r = reserva()
        r.registrar_llegada(r.intervalo.inicio + timedelta(minutes=14))
        assert r.estado is EstadoReserva.EN_USO

    def test_llegada_tarde_no_se_registra(self):
        r = reserva()
        with pytest.raises(TransicionInvalida):
            r.registrar_llegada(r.limite_de_llegada)

    def test_liberar_por_ausencia_es_idempotente(self):
        r = reserva()
        assert not r.liberar_por_ausencia(r.limite_de_llegada - timedelta(minutes=1))
        assert r.liberar_por_ausencia(r.limite_de_llegada)
        assert not r.liberar_por_ausencia(r.limite_de_llegada + timedelta(hours=1))
        assert r.estado is EstadoReserva.LIBERADA and not r.ocupa_la_maquina

    def test_una_reserva_en_uso_no_se_libera_ni_se_cancela(self):
        r = reserva()
        r.registrar_llegada(r.intervalo.inicio)
        assert not r.liberar_por_ausencia(r.limite_de_llegada)
        with pytest.raises(TransicionInvalida):
            r.cancelar()

    def test_activa_hasta_que_termina(self):
        r = reserva()
        assert r.esta_activa_en(r.intervalo.fin - timedelta(minutes=1))
        assert not r.esta_activa_en(r.intervalo.fin)


class TestMaquina:
    def test_fuera_de_servicio_y_reparada(self):
        m = Maquina("M1", "LAB-1", "L1-01")
        m.marcar_fuera_de_servicio()
        assert not m.en_servicio
        with pytest.raises(TransicionInvalida):
            m.marcar_fuera_de_servicio()
        m.marcar_reparada()
        assert m.en_servicio

    def test_campos_obligatorios(self):
        with pytest.raises(DatoInvalido):
            Maquina("M1", "", "L1-01")
        with pytest.raises(DatoInvalido):
            Laboratorio("LAB-1", "Lab", "")
