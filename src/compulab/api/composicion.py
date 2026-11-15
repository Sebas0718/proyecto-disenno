"""Raíz de composición: el ÚNICO lugar que conoce las clases concretas.

Aquí se decide qué adaptador recibe cada puerto (inyección de dependencias
manual, sin framework). Cambiar PostgreSQL por memoria, o el CSV por otro
formato, es cambiar una línea aquí; ningún caso de uso se entera.

Variables de entorno:
    COMPULAB_ALMACEN      "postgres" o "memoria" (por defecto: memoria)
    COMPULAB_DB_URL       URL de PostgreSQL (si el almacén es postgres)
    COMPULAB_DATOS_DEMO   "1" para cargar los datos de demostración si la base está vacía
    COMPULAB_ARCHIVOS     carpeta donde se escriben los CSV para Becas
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from compulab.aplicacion.casos_uso.asignar_turno import AsignarTurno
from compulab.aplicacion.casos_uso.cerrar_mes import CerrarMes
from compulab.aplicacion.casos_uso.liberar_reservas import LiberarReservasNoPresentadas
from compulab.aplicacion.casos_uso.reservar_maquina import ReservarMaquina
from compulab.aplicacion.casos_uso.responder_turno import ResponderTurnoPendiente
from compulab.aplicacion.consultas import Consultas
from compulab.aplicacion.puertos import FabricaDeUnidadDeTrabajo, Reloj
from compulab.infraestructura.datos_demo import cargar_datos_demo, usuarios_demo
from compulab.infraestructura.exportador_csv import ExportadorCsvBecas
from compulab.infraestructura.memoria import AlmacenEnMemoria, fabrica_en_memoria
from compulab.infraestructura.servicios import (
    DirectorioEnMemoria,
    NotificadorDeRegistro,
    RelojDelSistema,
)


@dataclass(frozen=True)
class Contenedor:
    """Todo lo que la API necesita, ya armado."""

    directorio: DirectorioEnMemoria
    notificador: NotificadorDeRegistro
    reloj: Reloj
    consultas: Consultas
    asignar_turno: AsignarTurno
    responder_turno: ResponderTurnoPendiente
    reservar_maquina: ReservarMaquina
    liberar_reservas: LiberarReservasNoPresentadas
    cerrar_mes: CerrarMes


def construir_contenedor(
    fabrica_uow: FabricaDeUnidadDeTrabajo,
    reloj: Reloj,
    carpeta_archivos: Path,
    directorio: DirectorioEnMemoria | None = None,
) -> Contenedor:
    directorio = directorio or DirectorioEnMemoria(usuarios_demo())
    notificador = NotificadorDeRegistro()
    return Contenedor(
        directorio=directorio,
        notificador=notificador,
        reloj=reloj,
        consultas=Consultas(fabrica_uow),
        asignar_turno=AsignarTurno(fabrica_uow, directorio, reloj, notificador),
        responder_turno=ResponderTurnoPendiente(fabrica_uow, directorio, notificador),
        reservar_maquina=ReservarMaquina(fabrica_uow, directorio, reloj),
        liberar_reservas=LiberarReservasNoPresentadas(fabrica_uow, reloj),
        cerrar_mes=CerrarMes(
            fabrica_uow, directorio, reloj, notificador, ExportadorCsvBecas(carpeta_archivos)
        ),
    )


def fabrica_desde_entorno() -> FabricaDeUnidadDeTrabajo:
    almacen = os.environ.get("COMPULAB_ALMACEN", "memoria")
    if almacen == "postgres":
        from compulab.infraestructura.postgres import fabrica_postgres

        return fabrica_postgres(os.environ["COMPULAB_DB_URL"])
    if almacen == "memoria":
        return fabrica_en_memoria(AlmacenEnMemoria())
    raise ValueError(f"COMPULAB_ALMACEN desconocido: {almacen!r}")


def contenedor_desde_entorno() -> Contenedor:
    reloj = RelojDelSistema()
    fabrica = fabrica_desde_entorno()
    if os.environ.get("COMPULAB_DATOS_DEMO", "1") == "1":
        with fabrica() as uow:
            if cargar_datos_demo(uow, reloj.ahora().date()):
                uow.confirmar()
    carpeta = Path(os.environ.get("COMPULAB_ARCHIVOS", "archivos"))
    return construir_contenedor(fabrica, reloj, carpeta)
