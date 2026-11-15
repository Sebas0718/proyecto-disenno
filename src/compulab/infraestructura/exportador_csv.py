"""Exportador del archivo para Becas en formato CSV (ADR-0012).

Formato (UTF-8, separador coma, punto decimal, una fila por asistente):

    anio,mes,asistente_id,nombre,categoria,horas_base,horas_con_recargo,horas_no_pagadas,monto_colones
    2026,10,A-01,Pablo Rojas,A,16.00,0.00,0.00,40000.00

El formato vive solo aquí: si Becas pide otro (JSON, Excel, columnas en otro
orden), se escribe otro adaptador de ``ExportadorPlanilla`` y se cambia una
línea en la raíz de composición.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from compulab.dominio.pagos.cierre import CierreMensual

ENCABEZADO = (
    "anio",
    "mes",
    "asistente_id",
    "nombre",
    "categoria",
    "horas_base",
    "horas_con_recargo",
    "horas_no_pagadas",
    "monto_colones",
)


def contenido_csv(cierre: CierreMensual) -> str:
    """Texto del archivo. Es una función pura: mismo cierre, mismo archivo."""
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(ENCABEZADO)
    for li in cierre.liquidaciones:
        escritor.writerow(
            (
                cierre.mes.anio,
                cierre.mes.numero,
                li.asistente_id,
                li.nombre,
                li.categoria.value,
                f"{li.horas_base:.2f}",
                f"{li.horas_con_recargo:.2f}",
                f"{li.horas_no_pagadas:.2f}",
                f"{li.monto.monto:.2f}",
            )
        )
    return salida.getvalue()


def nombre_de_archivo(cierre: CierreMensual) -> str:
    return f"becas-{cierre.mes.anio}-{cierre.mes.numero:02d}.csv"


class ExportadorCsvBecas:
    """Escribe el CSV en un directorio y devuelve la ruta."""

    def __init__(self, directorio: Path) -> None:
        self._directorio = directorio

    def exportar(self, cierre: CierreMensual) -> str:
        self._directorio.mkdir(parents=True, exist_ok=True)
        ruta = self._directorio / nombre_de_archivo(cierre)
        ruta.write_text(contenido_csv(cierre), encoding="utf-8")
        return str(ruta)
