"""Repositorios PostgreSQL con SQL plano (psycopg 3), sin ORM (ADR-0003).

Cada repositorio traduce filas a objetos del dominio y de vuelta. Las
violaciones de las restricciones EXCLUDE / PRIMARY KEY se traducen a los mismos
errores de dominio que lanzaría la política, así que para el caso de uso no
importa quién detectó el problema (ADR-0004).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any

import psycopg
from psycopg import errors

from compulab.dominio.comun.dinero import Dinero
from compulab.dominio.comun.errores import (
    ErrorDeDominio,
    LaboratorioYaCubierto,
    MaquinaOcupada,
    MesYaCerrado,
    TraslapeDeTurno,
)
from compulab.dominio.comun.tiempo import IntervaloTiempo, Mes
from compulab.dominio.horario.asistente import Asistente, Categoria, EstadoAsistente
from compulab.dominio.horario.disponibilidad import BloqueDisponible, DiaSemana, Disponibilidad
from compulab.dominio.horario.turno import EstadoTurno, Turno
from compulab.dominio.pagos.asistencia import Asistencia
from compulab.dominio.pagos.cierre import CierreMensual
from compulab.dominio.pagos.liquidacion import LiquidacionAsistente
from compulab.dominio.pagos.tarifario import Tarifario
from compulab.dominio.reservas.laboratorio import EstadoMaquina, Laboratorio, Maquina
from compulab.dominio.reservas.reserva import TOLERANCIA_DE_LLEGADA, EstadoReserva, Reserva

Fila = dict[str, Any]

# Nombre de la restricción en 001_esquema.sql -> error de dominio equivalente.
RESTRICCIONES: dict[str, tuple[type[ErrorDeDominio], str]] = {
    "turno_sin_traslape_del_asistente": (
        TraslapeDeTurno,
        "El asistente ya tiene un turno que se traslapa (otro coordinador lo asignó recién).",
    ),
    "turno_un_responsable_por_laboratorio": (
        LaboratorioYaCubierto,
        "El laboratorio ya tiene un turno en esa franja.",
    ),
    "reserva_sin_traslape_en_maquina": (
        MaquinaOcupada,
        "Otra persona acaba de reservar esa máquina en esa franja.",
    ),
    "cierre_mensual_pkey": (MesYaCerrado, "El mes ya fue cerrado."),
}


@contextmanager
def _traducir_restricciones() -> Iterator[None]:
    try:
        yield
    except (errors.ExclusionViolation, errors.UniqueViolation) as error:
        restriccion = error.diag.constraint_name or ""
        if restriccion in RESTRICCIONES:
            tipo, mensaje = RESTRICCIONES[restriccion]
            raise tipo(mensaje) from error
        raise


class _Base:
    def __init__(self, conexion: psycopg.Connection[Fila]) -> None:
        self._c = conexion

    def _uno(self, sql: str, params: tuple[Any, ...] = ()) -> Fila | None:
        return self._c.execute(sql, params).fetchone()

    def _todos(self, sql: str, params: tuple[Any, ...] = ()) -> list[Fila]:
        return self._c.execute(sql, params).fetchall()


# --- Laboratorios y máquinas --------------------------------------------------------


def _laboratorio(f: Fila) -> Laboratorio:
    return Laboratorio(f["id"], f["nombre"], f["campus"])


def _maquina(f: Fila) -> Maquina:
    return Maquina(f["id"], f["laboratorio_id"], f["codigo"], EstadoMaquina(f["estado"]))


class RepositorioLaboratoriosPostgres(_Base):
    def obtener(self, laboratorio_id: str) -> Laboratorio | None:
        fila = self._uno("SELECT * FROM laboratorio WHERE id = %s", (laboratorio_id,))
        return _laboratorio(fila) if fila else None

    def listar(self) -> list[Laboratorio]:
        return [_laboratorio(f) for f in self._todos("SELECT * FROM laboratorio ORDER BY id")]

    def agregar(self, laboratorio: Laboratorio) -> None:
        self._c.execute(
            "INSERT INTO laboratorio (id, nombre, campus) VALUES (%s, %s, %s)",
            (laboratorio.id, laboratorio.nombre, laboratorio.campus),
        )


class RepositorioMaquinasPostgres(_Base):
    def obtener(self, maquina_id: str) -> Maquina | None:
        fila = self._uno("SELECT * FROM maquina WHERE id = %s", (maquina_id,))
        return _maquina(fila) if fila else None

    def del_laboratorio(self, laboratorio_id: str) -> list[Maquina]:
        filas = self._todos(
            "SELECT * FROM maquina WHERE laboratorio_id = %s ORDER BY codigo", (laboratorio_id,)
        )
        return [_maquina(f) for f in filas]

    def agregar(self, maquina: Maquina) -> None:
        self._c.execute(
            "INSERT INTO maquina (id, laboratorio_id, codigo, estado) VALUES (%s, %s, %s, %s)",
            (maquina.id, maquina.laboratorio_id, maquina.codigo, maquina.estado.value),
        )


# --- Asistentes ----------------------------------------------------------------------


class RepositorioAsistentesPostgres(_Base):
    def _bloques(self, ids: list[str]) -> dict[str, list[BloqueDisponible]]:
        filas = self._todos("SELECT * FROM bloque_disponible WHERE asistente_id = ANY(%s)", (ids,))
        bloques: dict[str, list[BloqueDisponible]] = defaultdict(list)
        for f in filas:
            bloques[f["asistente_id"]].append(
                BloqueDisponible(DiaSemana(f["dia_semana"]), f["hora_inicio"], f["hora_fin"])
            )
        return bloques

    def _armar(self, filas: list[Fila]) -> list[Asistente]:
        bloques = self._bloques([f["id"] for f in filas])
        return [
            Asistente(
                f["id"],
                f["nombre"],
                Categoria(f["categoria"]),
                Decimal(f["tope_horas_semanales"]),
                Disponibilidad(bloques[f["id"]]),
                EstadoAsistente(f["estado"]),
            )
            for f in filas
        ]

    def obtener(self, asistente_id: str, *, bloquear: bool = False) -> Asistente | None:
        # FOR UPDATE: la fila queda bloqueada hasta el commit/rollback (ADR-0005).
        sql = "SELECT * FROM asistente WHERE id = %s" + (" FOR UPDATE" if bloquear else "")
        fila = self._uno(sql, (asistente_id,))
        return self._armar([fila])[0] if fila else None

    def listar(self) -> list[Asistente]:
        return self._armar(self._todos("SELECT * FROM asistente ORDER BY nombre"))

    def agregar(self, asistente: Asistente) -> None:
        self._c.execute(
            "INSERT INTO asistente (id, nombre, categoria, tope_horas_semanales, estado)"
            " VALUES (%s, %s, %s, %s, %s)",
            (
                asistente.id,
                asistente.nombre,
                asistente.categoria.value,
                asistente.tope_horas_semanales,
                asistente.estado.value,
            ),
        )
        for b in asistente.disponibilidad.bloques:
            self._c.execute(
                "INSERT INTO bloque_disponible (asistente_id, dia_semana, hora_inicio, hora_fin)"
                " VALUES (%s, %s, %s, %s)",
                (asistente.id, int(b.dia), b.hora_inicio, b.hora_fin),
            )


# --- Turnos ----------------------------------------------------------------------------


def _turno(f: Fila) -> Turno:
    return Turno(
        f["id"],
        f["laboratorio_id"],
        f["asistente_id"],
        IntervaloTiempo(f["inicio"], f["fin"]),
        EstadoTurno(f["estado"]),
        f["asignado_por"],
    )


class RepositorioTurnosPostgres(_Base):
    def siguiente_id(self) -> str:
        fila = self._uno("SELECT 'T-' || nextval('turno_numero') AS id")
        assert fila is not None
        return fila["id"]

    def obtener(self, turno_id: str) -> Turno | None:
        fila = self._uno("SELECT * FROM turno WHERE id = %s", (turno_id,))
        return _turno(fila) if fila else None

    def agregar(self, turno: Turno) -> None:
        with _traducir_restricciones():
            self._c.execute(
                "INSERT INTO turno (id, laboratorio_id, asistente_id, asignado_por, inicio, fin,"
                " estado) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    turno.id,
                    turno.laboratorio_id,
                    turno.asistente_id,
                    turno.asignado_por,
                    turno.intervalo.inicio,
                    turno.intervalo.fin,
                    turno.estado.value,
                ),
            )

    def actualizar(self, turno: Turno) -> None:
        with _traducir_restricciones():
            self._c.execute(
                "UPDATE turno SET estado = %s WHERE id = %s", (turno.estado.value, turno.id)
            )

    def del_asistente_en(self, asistente_id: str, periodo: IntervaloTiempo) -> list[Turno]:
        filas = self._todos(
            "SELECT * FROM turno WHERE asistente_id = %s AND inicio < %s AND fin > %s",
            (asistente_id, periodo.fin, periodo.inicio),
        )
        return [_turno(f) for f in filas]

    def del_laboratorio_en(self, laboratorio_id: str, periodo: IntervaloTiempo) -> list[Turno]:
        filas = self._todos(
            "SELECT * FROM turno WHERE laboratorio_id = %s AND inicio < %s AND fin > %s",
            (laboratorio_id, periodo.fin, periodo.inicio),
        )
        return [_turno(f) for f in filas]

    def pendientes_del_asistente(self, asistente_id: str) -> list[Turno]:
        filas = self._todos(
            "SELECT * FROM turno WHERE asistente_id = %s AND estado = 'PENDIENTE_ACEPTACION'",
            (asistente_id,),
        )
        return [_turno(f) for f in filas]


# --- Reservas ----------------------------------------------------------------------------


def _reserva(f: Fila) -> Reserva:
    return Reserva(
        f["id"],
        f["estudiante_id"],
        f["maquina_id"],
        IntervaloTiempo(f["inicio"], f["fin"]),
        EstadoReserva(f["estado"]),
    )


class RepositorioReservasPostgres(_Base):
    def siguiente_id(self) -> str:
        fila = self._uno("SELECT 'R-' || nextval('reserva_numero') AS id")
        assert fila is not None
        return fila["id"]

    def agregar(self, reserva: Reserva) -> None:
        with _traducir_restricciones():
            self._c.execute(
                "INSERT INTO reserva (id, estudiante_id, maquina_id, inicio, fin, estado)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    reserva.id,
                    reserva.estudiante_id,
                    reserva.maquina_id,
                    reserva.intervalo.inicio,
                    reserva.intervalo.fin,
                    reserva.estado.value,
                ),
            )

    def actualizar(self, reserva: Reserva) -> None:
        self._c.execute(
            "UPDATE reserva SET estado = %s WHERE id = %s", (reserva.estado.value, reserva.id)
        )

    def de_maquina_en(self, maquina_id: str, periodo: IntervaloTiempo) -> list[Reserva]:
        filas = self._todos(
            "SELECT * FROM reserva WHERE maquina_id = %s AND inicio < %s AND fin > %s",
            (maquina_id, periodo.fin, periodo.inicio),
        )
        return [_reserva(f) for f in filas]

    def del_estudiante_en(self, estudiante_id: str, periodo: IntervaloTiempo) -> list[Reserva]:
        filas = self._todos(
            "SELECT * FROM reserva WHERE estudiante_id = %s AND inicio < %s AND fin > %s",
            (estudiante_id, periodo.fin, periodo.inicio),
        )
        return [_reserva(f) for f in filas]

    def activas_del_estudiante(self, estudiante_id: str, ahora: datetime) -> list[Reserva]:
        filas = self._todos(
            "SELECT * FROM reserva WHERE estudiante_id = %s AND fin > %s"
            " AND estado IN ('ACTIVA', 'EN_USO')",
            (estudiante_id, ahora),
        )
        return [_reserva(f) for f in filas]

    def sin_presentarse(self, ahora: datetime) -> list[Reserva]:
        filas = self._todos(
            "SELECT * FROM reserva WHERE estado = 'ACTIVA' AND inicio + %s <= %s",
            (TOLERANCIA_DE_LLEGADA, ahora),
        )
        return [_reserva(f) for f in filas]


# --- Asistencias y tarifas -------------------------------------------------------------------


class RepositorioAsistenciasPostgres(_Base):
    def en(self, periodo: IntervaloTiempo) -> list[Asistencia]:
        filas = self._todos(
            "SELECT * FROM asistencia WHERE entrada >= %s AND entrada < %s ORDER BY entrada",
            (periodo.inicio, periodo.fin),
        )
        return [
            Asistencia(
                f["id"],
                f["turno_id"],
                f["asistente_id"],
                f["inicio_programado"],
                f["entrada"],
                f["salida"],
            )
            for f in filas
        ]

    def agregar(self, asistencia: Asistencia) -> None:
        self._c.execute(
            "INSERT INTO asistencia (id, turno_id, asistente_id, inicio_programado, entrada,"
            " salida) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                asistencia.id,
                asistencia.turno_id,
                asistencia.asistente_id,
                asistencia.inicio_programado,
                asistencia.trabajado.inicio,
                asistencia.trabajado.fin,
            ),
        )


class RepositorioTarifariosPostgres(_Base):
    def todos(self) -> list[Tarifario]:
        tarifas: dict[str, dict[Categoria, Dinero]] = defaultdict(dict)
        for f in self._todos("SELECT * FROM tarifa_categoria"):
            tarifas[f["tarifario_id"]][Categoria(f["categoria"])] = Dinero(f["monto_por_hora"])
        return [
            Tarifario(
                f["id"],
                f["vigente_desde"],
                f["vigente_hasta"],
                tarifas[f["id"]],
                Decimal(f["porcentaje_recargo"]),
            )
            for f in self._todos("SELECT * FROM tarifario ORDER BY vigente_desde")
        ]

    def agregar(self, tarifario: Tarifario) -> None:
        self._c.execute(
            "INSERT INTO tarifario (id, vigente_desde, vigente_hasta, porcentaje_recargo)"
            " VALUES (%s, %s, %s, %s)",
            (
                tarifario.id,
                tarifario.vigente_desde,
                tarifario.vigente_hasta,
                tarifario.porcentaje_recargo,
            ),
        )
        for categoria in Categoria:
            self._c.execute(
                "INSERT INTO tarifa_categoria (tarifario_id, categoria, monto_por_hora)"
                " VALUES (%s, %s, %s)",
                (tarifario.id, categoria.value, tarifario.tarifa_de(categoria).monto),
            )


# --- Cierres -----------------------------------------------------------------------------------


class RepositorioCierresPostgres(_Base):
    def existe(self, mes: Mes) -> bool:
        fila = self._uno(
            "SELECT 1 FROM cierre_mensual WHERE anio = %s AND mes = %s", (mes.anio, mes.numero)
        )
        return fila is not None

    def agregar(self, cierre: CierreMensual) -> None:
        with _traducir_restricciones():
            self._c.execute(
                "INSERT INTO cierre_mensual (anio, mes, cerrado_en) VALUES (%s, %s, %s)",
                (cierre.mes.anio, cierre.mes.numero, cierre.cerrado_en),
            )
        for li in cierre.liquidaciones:
            self._c.execute(
                "INSERT INTO liquidacion (anio, mes, asistente_id, nombre, categoria,"
                " minutos_base, minutos_con_recargo, minutos_no_pagados, monto)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    cierre.mes.anio,
                    cierre.mes.numero,
                    li.asistente_id,
                    li.nombre,
                    li.categoria.value,
                    li.minutos_base,
                    li.minutos_con_recargo,
                    li.minutos_no_pagados,
                    li.monto.monto,
                ),
            )

    def _armar(self, filas_cierre: list[Fila]) -> list[CierreMensual]:
        liquidaciones: dict[tuple[int, int], list[LiquidacionAsistente]] = defaultdict(list)
        for f in self._todos("SELECT * FROM liquidacion"):
            liquidaciones[(f["anio"], f["mes"])].append(
                LiquidacionAsistente(
                    asistente_id=f["asistente_id"],
                    nombre=f["nombre"],
                    categoria=Categoria(f["categoria"]),
                    minutos_base=f["minutos_base"],
                    minutos_con_recargo=f["minutos_con_recargo"],
                    minutos_no_pagados=f["minutos_no_pagados"],
                    monto=Dinero(f["monto"]),
                )
            )
        return [
            CierreMensual(
                Mes(f["anio"], f["mes"]),
                f["cerrado_en"],
                liquidaciones[(f["anio"], f["mes"])],
            )
            for f in filas_cierre
        ]

    def obtener(self, mes: Mes) -> CierreMensual | None:
        filas = self._todos(
            "SELECT * FROM cierre_mensual WHERE anio = %s AND mes = %s", (mes.anio, mes.numero)
        )
        cierres = self._armar(filas)
        return cierres[0] if cierres else None

    def listar(self) -> list[CierreMensual]:
        return self._armar(self._todos("SELECT * FROM cierre_mensual ORDER BY anio, mes"))
