"""Esquemas de entrada (pydantic) y conversión de objetos del dominio a JSON.

Pydantic valida el *formato* (que "dia" sea una fecha, que "acepta" sea
booleano). Las *reglas* las sigue validando el dominio. Los montos salen como
texto ("40000.00") para no perder precisión convirtiéndolos a float.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, Field

from compulab.aplicacion.consultas import CargaSemanal, OcupacionDelDia
from compulab.dominio.comun.tiempo import IntervaloTiempo
from compulab.dominio.comun.usuario import Usuario
from compulab.dominio.horario.turno import Turno
from compulab.dominio.pagos.cierre import CierreMensual
from compulab.dominio.reservas.reserva import Reserva

# --- Entrada -----------------------------------------------------------------------


class AsignarTurnoEntrada(BaseModel):
    laboratorio_id: str = Field(min_length=1)
    asistente_id: str = Field(min_length=1)
    dia: date
    hora_inicio: time
    hora_fin: time


class RespuestaTurnoEntrada(BaseModel):
    acepta: bool


class ReservarMaquinaEntrada(BaseModel):
    maquina_id: str = Field(min_length=1)
    inicio: datetime
    fin: datetime


class CerrarMesEntrada(BaseModel):
    anio: int
    mes: int


# --- Salida ------------------------------------------------------------------------


def intervalo_json(intervalo: IntervaloTiempo) -> dict[str, str]:
    return {"inicio": intervalo.inicio.isoformat(), "fin": intervalo.fin.isoformat()}


def usuario_json(usuario: Usuario, es_asistente: bool) -> dict[str, Any]:
    return {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "rol": usuario.rol.value,
        "laboratorio_id": usuario.laboratorio_id,
        "es_asistente": es_asistente,
    }


def turno_json(turno: Turno, nombres: dict[str, str] | None = None) -> dict[str, Any]:
    nombres = nombres or {}
    return {
        "id": turno.id,
        "laboratorio_id": turno.laboratorio_id,
        "asistente_id": turno.asistente_id,
        "asistente_nombre": nombres.get(turno.asistente_id, turno.asistente_id),
        "estado": turno.estado.value,
        "horas": turno.intervalo.minutos / 60,
        **intervalo_json(turno.intervalo),
    }


def carga_json(carga: CargaSemanal) -> dict[str, Any]:
    a = carga.asistente
    return {
        "id": a.id,
        "nombre": a.nombre,
        "categoria": a.categoria.value,
        "estado": a.estado.value,
        "activo": a.esta_activo,
        "tope_horas": float(a.tope_horas_semanales),
        "horas_asignadas": carga.minutos_asignados / 60,
        "disponibilidad": [
            {
                "dia": int(b.dia),
                "hora_inicio": b.hora_inicio.isoformat("minutes"),
                "hora_fin": b.hora_fin.isoformat("minutes"),
            }
            for b in a.disponibilidad.bloques
        ],
    }


def reserva_json(reserva: Reserva) -> dict[str, Any]:
    return {
        "id": reserva.id,
        "maquina_id": reserva.maquina_id,
        "estado": reserva.estado.value,
        "limite_de_llegada": reserva.limite_de_llegada.isoformat(),
        **intervalo_json(reserva.intervalo),
    }


def ocupacion_json(ocupacion: OcupacionDelDia, estudiante_id: str) -> dict[str, Any]:
    return {
        "laboratorio": {
            "id": ocupacion.laboratorio.id,
            "nombre": ocupacion.laboratorio.nombre,
            "campus": ocupacion.laboratorio.campus,
        },
        "franjas_abiertas": [intervalo_json(i) for i in ocupacion.franjas_abiertas],
        "maquinas": [
            {
                "id": om.maquina.id,
                "codigo": om.maquina.codigo,
                "en_servicio": om.maquina.en_servicio,
                "reservas": [
                    {**intervalo_json(r.intervalo), "propia": r.estudiante_id == estudiante_id}
                    for r in om.reservas
                ],
            }
            for om in ocupacion.maquinas
        ],
    }


def cierre_json(cierre: CierreMensual, con_detalle: bool = True) -> dict[str, Any]:
    datos: dict[str, Any] = {
        "anio": cierre.mes.anio,
        "mes": cierre.mes.numero,
        "cerrado_en": cierre.cerrado_en.isoformat(),
        "total": f"{cierre.total.monto:.2f}",
        "asistentes": len(cierre.liquidaciones),
        "con_horas_no_pagadas": len(cierre.con_horas_no_pagadas),
    }
    if con_detalle:
        datos["liquidaciones"] = [
            {
                "asistente_id": li.asistente_id,
                "nombre": li.nombre,
                "categoria": li.categoria.value,
                "horas_base": f"{li.horas_base:.2f}",
                "horas_con_recargo": f"{li.horas_con_recargo:.2f}",
                "horas_no_pagadas": f"{li.horas_no_pagadas:.2f}",
                "monto": f"{li.monto.monto:.2f}",
            }
            for li in cierre.liquidaciones
        ]
    return datos
