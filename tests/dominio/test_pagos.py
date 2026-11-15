"""Invariantes de Tarifario, CatalogoDeTarifas, Asistencia, Liquidación y Cierre."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.errores import DatoInvalido, MesNoTerminado, SinTarifarioVigente
from compulab.dominio.comun.tiempo import Mes
from compulab.dominio.horario.asistente import Categoria
from compulab.dominio.pagos.asistencia import Asistencia
from compulab.dominio.pagos.cierre import CierreMensual
from compulab.dominio.pagos.liquidacion import LiquidacionAsistente
from compulab.dominio.pagos.recargo import RecargoNocturnoOFinDeSemana
from compulab.dominio.pagos.tarifario import CatalogoDeTarifas, Tarifario

TARIFAS = {Categoria.A: Dinero(Decimal(1000)), Categoria.B: Dinero(Decimal(2000))}


class TestTarifario:
    def test_necesita_tarifa_para_las_dos_categorias(self):
        with pytest.raises(DatoInvalido):
            Tarifario("T", date(2026, 1, 1), None, {Categoria.A: Dinero(Decimal(1))}, Decimal(50))

    def test_tarifa_positiva(self):
        tarifas = {**TARIFAS, Categoria.B: Dinero(Decimal(0))}
        with pytest.raises(DatoInvalido):
            Tarifario("T", date(2026, 1, 1), None, tarifas, Decimal(50))

    def test_vigencia_coherente_y_recargo_no_negativo(self):
        with pytest.raises(DatoInvalido):
            Tarifario("T", date(2026, 2, 1), date(2026, 1, 1), TARIFAS, Decimal(50))
        with pytest.raises(DatoInvalido):
            Tarifario("T", date(2026, 1, 1), None, TARIFAS, Decimal(-1))

    def test_factor_de_recargo(self):
        assert Tarifario("T", date(2026, 1, 1), None, TARIFAS, Decimal(50)).factor_de_recargo == (
            Decimal("1.5")
        )

    def test_catalogo_no_admite_vigencias_traslapadas(self):
        t1 = Tarifario("T1", date(2026, 1, 1), date(2026, 6, 30), TARIFAS, Decimal(50))
        t2 = Tarifario("T2", date(2026, 6, 30), None, TARIFAS, Decimal(50))
        with pytest.raises(DatoInvalido):
            CatalogoDeTarifas([t1, t2])

    def test_catalogo_encuentra_el_vigente_o_falla(self):
        t1 = Tarifario("T1", date(2026, 1, 1), date(2026, 6, 30), TARIFAS, Decimal(50))
        t2 = Tarifario("T2", date(2026, 7, 1), None, TARIFAS, Decimal(25))
        catalogo = CatalogoDeTarifas([t2, t1])
        assert catalogo.vigente_en(date(2026, 7, 1)).id == "T2"
        with pytest.raises(SinTarifarioVigente):
            catalogo.vigente_en(date(2025, 12, 31))


class TestAsistenciaYRecargo:
    def test_salida_posterior_a_la_entrada(self):
        with pytest.raises(DatoInvalido):
            momento = datetime(2026, 10, 6, 8)
            Asistencia("AS", "T", "A1", momento, momento, momento)

    @pytest.mark.parametrize(
        ("inicio", "esperado"),
        [
            (datetime(2026, 10, 6, 17, 59), False),  # martes 17:59
            (datetime(2026, 10, 6, 18, 0), True),  # martes 18:00
            (datetime(2026, 10, 10, 8, 0), True),  # sábado
            (datetime(2026, 10, 11, 8, 0), True),  # domingo
        ],
    )
    def test_regla_de_recargo(self, inicio, esperado):
        a = Asistencia("AS", "T", "A1", inicio, inicio, inicio.replace(hour=23))
        assert RecargoNocturnoOFinDeSemana().aplica(a) is esperado


class TestLiquidacionYCierre:
    def liquidacion(self, asistente_id: str = "A1", **cambios) -> LiquidacionAsistente:
        datos = dict(
            asistente_id=asistente_id,
            nombre="Ana",
            categoria=Categoria.A,
            minutos_base=60,
            minutos_con_recargo=0,
            minutos_no_pagados=0,
            monto=Dinero(Decimal(1000)),
        )
        datos.update(cambios)
        return LiquidacionAsistente(**datos)

    def test_horas_no_negativas(self):
        with pytest.raises(DatoInvalido):
            self.liquidacion(minutos_no_pagados=-1)

    def test_sin_horas_pagadas_no_hay_monto(self):
        with pytest.raises(DatoInvalido):
            self.liquidacion(minutos_base=0)

    def test_cierre_solo_de_un_mes_terminado(self):
        with pytest.raises(MesNoTerminado):
            CierreMensual(Mes(2026, 10), datetime(2026, 10, 31, 12), [])

    def test_cierre_una_liquidacion_por_asistente(self):
        with pytest.raises(DatoInvalido):
            CierreMensual(
                Mes(2026, 10), datetime(2026, 11, 1), [self.liquidacion(), self.liquidacion()]
            )

    def test_total_del_cierre(self):
        cierre = CierreMensual(
            Mes(2026, 10), datetime(2026, 11, 1), [self.liquidacion("A1"), self.liquidacion("A2")]
        )
        assert cierre.total == Dinero(Decimal(2000))
        assert not hasattr(cierre, "agregar")  # inmutable: no hay forma de modificarlo
