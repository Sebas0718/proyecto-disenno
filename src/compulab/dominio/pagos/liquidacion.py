"""Liquidación mensual de un asistente (cálculo del pago).

Reglas del enunciado:
- Se paga lo trabajado según las marcas de entrada y salida.
- Tarifa base: la de su categoría; recargo para turnos nocturnos o de fin de semana.
- "Las horas trabajadas por encima del tope semanal no se pagan [...] quedan
  registradas y sin pagar, y el coordinador de soporte tiene que saberlo."

Decisiones (ADR-0007 y ADR-0008):
- La semana es ISO (lunes a domingo). Si la primera semana del mes empezó en
  el mes anterior, esas horas cuentan para el tope aunque ya se hayan pagado
  en el cierre anterior.
- Dentro de una semana se paga en orden cronológico hasta llegar al tope; lo
  que sobra (las últimas horas) queda sin pagar.
- Se cuenta por minutos enteros y el monto se redondea a céntimos al final.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.errores import DatoInvalido
from compulab.dominio.comun.tiempo import Mes, SemanaISO
from compulab.dominio.horario.asistente import Asistente, Categoria
from compulab.dominio.pagos.asistencia import Asistencia
from compulab.dominio.pagos.recargo import PoliticaDeRecargo, RecargoNocturnoOFinDeSemana
from compulab.dominio.pagos.tarifario import CatalogoDeTarifas

SESENTA = Decimal(60)
CENTESIMAS = Decimal("0.01")


def _a_horas(minutos: int) -> Decimal:
    return (Decimal(minutos) / SESENTA).quantize(CENTESIMAS)


@dataclass(frozen=True, slots=True)
class LiquidacionAsistente:
    """Resultado del cálculo para un asistente en un mes. Inmutable."""

    asistente_id: str
    nombre: str
    categoria: Categoria
    minutos_base: int
    minutos_con_recargo: int
    minutos_no_pagados: int
    monto: Dinero

    def __post_init__(self) -> None:
        minutos = (self.minutos_base, self.minutos_con_recargo, self.minutos_no_pagados)
        if any(not isinstance(m, int) or m < 0 for m in minutos):
            raise DatoInvalido("Las horas de una liquidación no pueden ser negativas.")
        if self.minutos_base + self.minutos_con_recargo == 0 and self.monto.monto != 0:
            raise DatoInvalido("No puede haber monto a pagar sin horas pagadas.")

    @property
    def horas_base(self) -> Decimal:
        return _a_horas(self.minutos_base)

    @property
    def horas_con_recargo(self) -> Decimal:
        return _a_horas(self.minutos_con_recargo)

    @property
    def horas_no_pagadas(self) -> Decimal:
        return _a_horas(self.minutos_no_pagados)

    @property
    def tiene_horas_no_pagadas(self) -> bool:
        return self.minutos_no_pagados > 0


class LiquidadorMensual:
    """Servicio de dominio que calcula una ``LiquidacionAsistente``."""

    def __init__(self, politica_de_recargo: PoliticaDeRecargo | None = None) -> None:
        self._recargo = politica_de_recargo or RecargoNocturnoOFinDeSemana()

    def liquidar(
        self,
        mes: Mes,
        asistente: Asistente,
        asistencias: Iterable[Asistencia],
        tarifas: CatalogoDeTarifas,
    ) -> LiquidacionAsistente:
        """``asistencias`` incluye las de la primera semana que caen en el mes anterior."""
        lista = sorted(asistencias, key=lambda a: a.trabajado.inicio)
        if any(a.asistente_id != asistente.id for a in lista):
            raise DatoInvalido("Las asistencias deben ser del asistente que se liquida.")

        tope = asistente.tope_minutos_semanales
        usados_por_semana: dict[SemanaISO, int] = {}
        minutos_base = minutos_recargo = minutos_no_pagados = 0
        monto = Dinero.cero()

        for asistencia in lista:
            fecha = asistencia.trabajado.inicio.date()
            if fecha >= mes.siguiente().primer_dia:
                continue  # posterior al mes: no cambia nada de este cierre
            semana = SemanaISO.de(fecha)
            usados = usados_por_semana.get(semana, 0)
            trabajados = asistencia.minutos_trabajados
            pagables = min(trabajados, max(tope - usados, 0))
            usados_por_semana[semana] = usados + trabajados

            if not mes.contiene(fecha):
                continue  # del mes anterior: solo cuenta para el tope de la semana

            tarifario = tarifas.vigente_en(fecha)
            tarifa = tarifario.tarifa_de(asistente.categoria)
            horas_pagables = Decimal(pagables) / SESENTA
            if self._recargo.aplica(asistencia):
                minutos_recargo += pagables
                monto += tarifa.por(horas_pagables * tarifario.factor_de_recargo)
            else:
                minutos_base += pagables
                monto += tarifa.por(horas_pagables)
            minutos_no_pagados += trabajados - pagables

        return LiquidacionAsistente(
            asistente_id=asistente.id,
            nombre=asistente.nombre,
            categoria=asistente.categoria,
            minutos_base=minutos_base,
            minutos_con_recargo=minutos_recargo,
            minutos_no_pagados=minutos_no_pagados,
            monto=monto.redondeado(),
        )
