"""Invariantes y comportamiento de Asistente, Disponibilidad, Turno y la política."""

from datetime import time
from decimal import Decimal

import pytest

from compulab.dominio.comun.errores import (
    DatoInvalido,
    TopeSemanalExcedido,
    TransicionInvalida,
)
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.horario.asistente import Asistente, Categoria, EstadoAsistente
from compulab.dominio.horario.disponibilidad import BloqueDisponible, DiaSemana, Disponibilidad
from compulab.dominio.horario.politica_asignacion import (
    DentroDelTopeSemanal,
    PoliticaDeAsignacion,
    SolicitudDeAsignacion,
)
from compulab.dominio.horario.turno import EstadoTurno, Turno
from tests.dobles import AHORA, asistente, dia, en


class TestDisponibilidad:
    def test_bloque_debe_terminar_despues_de_empezar(self):
        with pytest.raises(DatoInvalido):
            BloqueDisponible(DiaSemana.LUNES, time(10), time(9))

    def test_incluye_solo_el_dia_y_las_horas_declaradas(self):
        disponibilidad = Disponibilidad([BloqueDisponible(DiaSemana.LUNES, time(8), time(12))])
        assert disponibilidad.incluye(en(dia(0), 8, 12))
        assert not disponibilidad.incluye(en(dia(0), 11, 13))
        assert not disponibilidad.incluye(en(dia(1), 8, 10))  # martes

    def test_bloques_seguidos_se_suman(self):
        disponibilidad = Disponibilidad(
            [
                BloqueDisponible(DiaSemana.LUNES, time(8), time(10)),
                BloqueDisponible(DiaSemana.LUNES, time(10), time(12)),
            ]
        )
        assert disponibilidad.incluye(en(dia(0), 9, 11))


class TestAsistente:
    @pytest.mark.parametrize("tope", [Decimal(0), Decimal(-1), Decimal(169)])
    def test_tope_fuera_de_rango(self, tope):
        with pytest.raises(DatoInvalido):
            Asistente("A", "Ana", Categoria.A, tope, Disponibilidad([]))

    def test_tope_debe_ser_decimal(self):
        with pytest.raises(DatoInvalido):
            Asistente("A", "Ana", Categoria.A, 10, Disponibilidad([]))  # type: ignore[arg-type]

    def test_categoria_debe_ser_una_de_las_dos(self):
        with pytest.raises(DatoInvalido):
            Asistente("A", "Ana", "C", Decimal(10), Disponibilidad([]))  # type: ignore[arg-type]

    def test_renunciar_y_dar_de_baja(self):
        a = asistente()
        a.renunciar()
        assert a.estado is EstadoAsistente.RENUNCIO and not a.esta_activo
        with pytest.raises(TransicionInvalida):
            a.dar_de_baja()

    def test_corregir_tope_tambien_valida(self):
        a = asistente(tope=10)
        a.corregir_tope(Decimal("12.5"))
        assert a.tope_minutos_semanales == 750
        with pytest.raises(DatoInvalido):
            a.corregir_tope(Decimal(0))


class TestTurno:
    def test_exactamente_un_asistente_responsable(self):
        with pytest.raises(DatoInvalido):
            Turno("T", "LAB-1", "", en(dia(0), 8, 10), EstadoTurno.CONFIRMADO, "CL1")

    def test_empieza_y_termina_el_mismo_dia(self):
        intervalo = IntervaloTiempo(en(dia(0), 22, 23).inicio, en(dia(1), 1, 2).inicio)
        with pytest.raises(DatoInvalido):
            Turno("T", "LAB-1", "A1", intervalo, EstadoTurno.CONFIRMADO, "CL1")

    def test_solo_un_pendiente_se_acepta_o_rechaza(self):
        t = Turno("T", "LAB-1", "A1", en(dia(0), 8, 10), EstadoTurno.PENDIENTE_ACEPTACION, "CL1")
        assert t.vigente and not t.confirmado
        t.aceptar()
        assert t.confirmado
        with pytest.raises(TransicionInvalida):
            t.rechazar()

    def test_un_rechazado_deja_de_estar_vigente(self):
        t = Turno("T", "LAB-1", "A1", en(dia(0), 8, 10), EstadoTurno.PENDIENTE_ACEPTACION, "CL1")
        t.rechazar()
        assert not t.vigente


class TestPolitica:
    def solicitud(self, **cambios) -> SolicitudDeAsignacion:
        datos = dict(
            asistente=asistente("A1", tope=4),
            laboratorio_id="LAB-1",
            intervalo=en(dia(0), 8, 10),
            turnos_de_la_semana=(),
            turnos_del_laboratorio=(),
            ahora=AHORA,
        )
        datos.update(cambios)
        return SolicitudDeAsignacion(**datos)

    def test_la_solicitud_no_mezcla_turnos_de_otro_asistente(self):
        ajeno = Turno("T", "LAB-1", "OTRO", en(dia(1), 8, 10), EstadoTurno.CONFIRMADO, "CL1")
        with pytest.raises(DatoInvalido):
            self.solicitud(turnos_de_la_semana=(ajeno,))

    def test_los_pendientes_tambien_cuentan_para_el_tope(self):
        pendiente = Turno(
            "T", "LAB-2", "A1", en(dia(1), 8, 11), EstadoTurno.PENDIENTE_ACEPTACION, "CL2"
        )
        with pytest.raises(TopeSemanalExcedido):
            DentroDelTopeSemanal().verificar(self.solicitud(turnos_de_la_semana=(pendiente,)))

    def test_las_reglas_se_pueden_reemplazar(self):
        """Specification: una política sin reglas solo decide el estado inicial."""
        politica = PoliticaDeAsignacion(reglas=())
        turno = politica.asignar("T", "CL1", self.solicitud(intervalo=en(dia(5), 8, 20)))
        assert turno.estado is EstadoTurno.PENDIENTE_ACEPTACION
