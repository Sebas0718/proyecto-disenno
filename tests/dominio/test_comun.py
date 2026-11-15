"""Invariantes de los objetos de valor y de Usuario."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime, time
from decimal import Decimal

import pytest

from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.errores import DatoInvalido, IntervaloInvalido
from compulab.dominio.comun.tiempo import IntervaloTiempo, Mes, SemanaISO, cubren
from compulab.dominio.comun.usuario import Rol, Usuario


def iv(h1: int, h2: int, d: int = 16) -> IntervaloTiempo:
    return IntervaloTiempo.en_dia(date(2026, 11, d), time(h1), time(h2))


class TestIntervaloTiempo:
    def test_fin_debe_ser_posterior_al_inicio(self):
        with pytest.raises(IntervaloInvalido):
            iv(10, 10)
        with pytest.raises(IntervaloInvalido):
            iv(11, 10)

    def test_rechaza_horas_con_zona_horaria(self):
        from datetime import UTC

        with pytest.raises(DatoInvalido):
            IntervaloTiempo(
                datetime(2026, 1, 1, 8, tzinfo=UTC), datetime(2026, 1, 1, 9, tzinfo=UTC)
            )

    def test_es_inmutable(self):
        intervalo = iv(8, 9)
        with pytest.raises(FrozenInstanceError):
            intervalo.inicio = datetime(2026, 1, 1)  # type: ignore[misc]

    def test_traslape(self):
        assert iv(8, 10).se_traslapa_con(iv(9, 11))
        assert iv(8, 12).se_traslapa_con(iv(9, 10))
        assert not iv(8, 10).se_traslapa_con(iv(10, 12))  # seguidos
        assert not iv(8, 10, d=16).se_traslapa_con(iv(8, 10, d=17))

    def test_minutos_y_semana(self):
        assert iv(8, 10).minutos == 120
        assert iv(8, 10).semana == SemanaISO(2026, 47)

    def test_cubren_sin_huecos(self):
        assert cubren([iv(8, 10), iv(10, 12)], iv(9, 11))
        assert not cubren([iv(8, 10), iv(10, 12)], iv(11, 13))
        assert not cubren([iv(8, 9), iv(10, 12)], iv(8, 11))  # hueco de 9 a 10
        assert cubren([iv(10, 12), iv(7, 10)], iv(8, 11))  # el orden no importa
        assert not cubren([], iv(8, 9))


class TestSemanaYMes:
    def test_semana_iso_va_de_lunes_a_lunes(self):
        semana = SemanaISO.de(date(2026, 11, 22))  # domingo
        assert semana.lunes == date(2026, 11, 16)
        assert semana.intervalo.minutos == 7 * 24 * 60

    def test_semana_que_no_existe(self):
        with pytest.raises(DatoInvalido):
            SemanaISO(2026, 54)

    @pytest.mark.parametrize("numero", [0, 13])
    def test_mes_invalido(self, numero):
        with pytest.raises(DatoInvalido):
            Mes(2026, numero)

    def test_mes_termina_cuando_empieza_el_siguiente(self):
        diciembre = Mes(2026, 12)
        assert diciembre.siguiente() == Mes(2027, 1)
        assert not diciembre.termino_en(datetime(2026, 12, 31, 23, 59))
        assert diciembre.termino_en(datetime(2027, 1, 1, 0, 0))


class TestDinero:
    def test_no_acepta_float(self):
        with pytest.raises(DatoInvalido):
            Dinero(0.1)  # type: ignore[arg-type]

    def test_no_acepta_negativos(self):
        with pytest.raises(DatoInvalido):
            Dinero(Decimal("-1"))

    def test_suma_multiplica_y_redondea_hacia_arriba_el_medio_centimo(self):
        total = Dinero(Decimal("0.1")) + Dinero(Decimal("0.2"))
        assert total == Dinero(Decimal("0.3"))
        assert Dinero(Decimal("10")).por(Decimal("0.0005")).redondeado() == Dinero(Decimal("0.01"))


class TestUsuario:
    def test_coordinador_de_laboratorio_necesita_laboratorio(self):
        with pytest.raises(DatoInvalido):
            Usuario("C", "Coord", Rol.COORDINADOR_LABORATORIO)

    def test_solo_el_coordinador_de_laboratorio_tiene_laboratorio(self):
        with pytest.raises(DatoInvalido):
            Usuario("E", "Est", Rol.ESTUDIANTE, "LAB-1")

    def test_campos_obligatorios(self):
        with pytest.raises(DatoInvalido):
            Usuario(" ", "Nombre", Rol.ESTUDIANTE)

    def test_permisos(self):
        soporte = Usuario("S", "Soporte", Rol.COORDINADOR_SOPORTE)
        coord = Usuario("C", "Coord", Rol.COORDINADOR_LABORATORIO, "LAB-1")
        estudiante = Usuario("E", "Est", Rol.ESTUDIANTE)
        assert soporte.puede_administrar_horario("LAB-3")
        assert coord.puede_administrar_horario("LAB-1")
        assert not coord.puede_administrar_horario("LAB-2")
        assert not estudiante.puede_administrar_horario("LAB-1")
        assert estudiante.puede_reservar() and not coord.puede_reservar()
        assert soporte.puede_cerrar_mes() and not coord.puede_cerrar_mes()

    def test_los_atributos_son_de_solo_lectura(self):
        usuario = Usuario("E", "Est", Rol.ESTUDIANTE)
        with pytest.raises(AttributeError):
            usuario.rol = Rol.COORDINADOR_SOPORTE  # type: ignore[misc]
