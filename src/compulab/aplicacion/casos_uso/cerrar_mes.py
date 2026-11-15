"""CU-19 Cerrar el mes (contrato CO-03, docs/02-casos-de-uso.md)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time

from compulab.aplicacion.casos_uso.comun import existente, identificar
from compulab.aplicacion.puertos import (
    DirectorioInstitucional,
    ExportadorPlanilla,
    FabricaDeUnidadDeTrabajo,
    Notificador,
    Reloj,
)
from compulab.dominio.comun.errores import MesNoTerminado, MesYaCerrado, NoAutorizado
from compulab.dominio.comun.tiempo import IntervaloTiempo, Mes, SemanaISO
from compulab.dominio.pagos.asistencia import Asistencia
from compulab.dominio.pagos.cierre import CierreMensual
from compulab.dominio.pagos.liquidacion import LiquidadorMensual
from compulab.dominio.pagos.tarifario import CatalogoDeTarifas


@dataclass(frozen=True, slots=True)
class CerrarMesComando:
    solicitante_id: str
    anio: int
    mes: int


@dataclass(frozen=True, slots=True)
class MesCerrado:
    cierre: CierreMensual
    archivo: str


def periodo_de_calculo(mes: Mes) -> IntervaloTiempo:
    """Desde el lunes de la semana del día 1 hasta el fin del mes.

    Incluye los días del mes anterior que comparten semana con el día 1, porque
    cuentan para el tope semanal (ADR-0007).
    """
    lunes = SemanaISO.de(mes.primer_dia).lunes
    return IntervaloTiempo(datetime.combine(lunes, time.min), mes.intervalo.fin)


class CerrarMes:
    def __init__(
        self,
        fabrica_uow: FabricaDeUnidadDeTrabajo,
        directorio: DirectorioInstitucional,
        reloj: Reloj,
        notificador: Notificador,
        exportador: ExportadorPlanilla,
        liquidador: LiquidadorMensual | None = None,
    ) -> None:
        self._fabrica_uow = fabrica_uow
        self._directorio = directorio
        self._reloj = reloj
        self._notificador = notificador
        self._exportador = exportador
        self._liquidador = liquidador or LiquidadorMensual()

    def ejecutar(self, comando: CerrarMesComando) -> MesCerrado:
        # Paso 2: solo la Coordinación de Soporte cierra el mes.
        solicitante = identificar(self._directorio, comando.solicitante_id)
        if not solicitante.puede_cerrar_mes():
            raise NoAutorizado("Solo el coordinador de soporte puede cerrar el mes.")
        # Paso 3: el mes terminó y no estaba cerrado.
        mes = Mes(comando.anio, comando.mes)
        ahora = self._reloj.ahora()
        if not mes.termino_en(ahora):
            raise MesNoTerminado(f"El mes {mes} todavía no ha terminado; no se puede cerrar.")
        with self._fabrica_uow() as uow:
            if uow.cierres.existe(mes):
                raise MesYaCerrado(
                    f"El mes {mes} ya se cerró; un mes cerrado no se vuelve a calcular."
                )
            # Paso 4: asistencias del periodo y tarifas.
            tarifas = CatalogoDeTarifas(uow.tarifarios.todos())
            por_asistente: dict[str, list[Asistencia]] = defaultdict(list)
            for asistencia in uow.asistencias.en(periodo_de_calculo(mes)):
                por_asistente[asistencia.asistente_id].append(asistencia)
            # Paso 5: una liquidación por asistente que trabajó en el mes.
            liquidaciones = []
            for asistente_id, asistencias in por_asistente.items():
                if not any(mes.contiene(a.trabajado.inicio.date()) for a in asistencias):
                    continue
                asistente = existente(
                    uow.asistentes.obtener(asistente_id), f"el asistente {asistente_id}"
                )
                liquidacion = self._liquidador.liquidar(mes, asistente, asistencias, tarifas)
                liquidaciones.append(liquidacion)
            # Pasos 6 y 7: registrar el cierre y generar el archivo, en la misma transacción.
            cierre = CierreMensual(mes, ahora, liquidaciones)
            uow.cierres.agregar(cierre)
            archivo = self._exportador.exportar(cierre)
            uow.confirmar()

        # Extensión 5a: el coordinador de soporte tiene que saber de las horas no pagadas.
        if cierre.con_horas_no_pagadas:
            detalle = "; ".join(
                f"{li.nombre}: {li.horas_no_pagadas} h" for li in cierre.con_horas_no_pagadas
            )
            self._notificador.notificar(
                solicitante.id,
                f"Horas trabajadas sin pagar en {mes}",
                f"Se trabajaron horas por encima del tope semanal que no se pagan: {detalle}.",
            )
        return MesCerrado(cierre=cierre, archivo=archivo)
