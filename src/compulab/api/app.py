"""API HTTP de CompuLab (adaptador de entrada).

Cada endpoint hace tres cosas y nada más:
  1. identifica al solicitante (cabecera ``X-Usuario-Id``, que simula la
     sesión del directorio institucional; ADR-0011);
  2. llama a un caso de uso o a una consulta;
  3. convierte el resultado (o el error de dominio) a JSON / HTTP.

Arranque:  uvicorn compulab.api.app:app_desde_entorno --factory
"""

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from compulab.api.composicion import Contenedor, contenedor_desde_entorno
from compulab.api.esquemas import (
    AsignarTurnoEntrada,
    CerrarMesEntrada,
    ReservarMaquinaEntrada,
    RespuestaTurnoEntrada,
    carga_json,
    cierre_json,
    ocupacion_json,
    reserva_json,
    turno_json,
    usuario_json,
)
from compulab.aplicacion.casos_uso.asignar_turno import AsignarTurnoComando
from compulab.aplicacion.casos_uso.cerrar_mes import CerrarMesComando
from compulab.aplicacion.casos_uso.reservar_maquina import ReservarMaquinaComando
from compulab.aplicacion.casos_uso.responder_turno import ResponderTurnoComando
from compulab.dominio.comun.errores import (
    DatoInvalido,
    ErrorDeDominio,
    NoAutorizado,
    NoEncontrado,
    ReglaDeNegocioViolada,
)
from compulab.dominio.comun.tiempo import Mes, SemanaISO
from compulab.dominio.comun.usuario import Usuario
from compulab.infraestructura.exportador_csv import contenido_csv, nombre_de_archivo

registro = logging.getLogger("compulab.api")

CARPETA_WEB = Path(os.environ.get("COMPULAB_WEB", Path(__file__).resolve().parents[3] / "web"))
SEGUNDOS_ENTRE_LIBERACIONES = 60

# Error de dominio -> código HTTP. 409 "Conflict": los datos están bien, pero una
# regla del negocio impide la operación.
CODIGOS_HTTP: list[tuple[type[ErrorDeDominio], int]] = [
    (NoAutorizado, 403),
    (NoEncontrado, 404),
    (DatoInvalido, 422),
    (ReglaDeNegocioViolada, 409),
]


def codigo_http(error: ErrorDeDominio) -> int:
    for tipo, codigo in CODIGOS_HTTP:
        if isinstance(error, tipo):
            return codigo
    return 400


def crear_app(contenedor: Contenedor, liberar_en_segundo_plano: bool = True) -> FastAPI:
    @contextlib.asynccontextmanager
    async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
        tarea = None
        if liberar_en_segundo_plano:
            tarea = asyncio.create_task(_liberar_periodicamente(contenedor))
        yield
        if tarea:
            tarea.cancel()

    app = FastAPI(
        title="CompuLab",
        description="Administración de los laboratorios de la Escuela de Computación.",
        version="0.1.0",
        lifespan=ciclo_de_vida,
    )

    @app.exception_handler(ErrorDeDominio)
    async def error_de_dominio(_: Request, error: ErrorDeDominio) -> JSONResponse:
        return JSONResponse(
            status_code=codigo_http(error),
            content={"codigo": error.codigo, "mensaje": error.mensaje},
        )

    def solicitante(x_usuario_id: Annotated[str | None, Header()] = None) -> Usuario:
        usuario = contenedor.directorio.buscar(x_usuario_id or "")
        if usuario is None:
            raise HTTPException(status_code=401, detail="Debe identificarse para continuar.")
        return usuario

    Solicitante = Annotated[Usuario, Depends(solicitante)]
    nombres = {u.id: u.nombre for u in contenedor.directorio.listar()}
    consultas = contenedor.consultas

    def es_asistente(usuario: Usuario) -> bool:
        return consultas.asistente(usuario.id) is not None

    # --- Sesión -------------------------------------------------------------------
    @app.get("/api/salud")
    def salud() -> dict[str, str]:
        return {"estado": "ok"}

    @app.get("/api/usuarios")
    def usuarios() -> list[dict[str, Any]]:
        """Lista del directorio simulado, para elegir con quién entrar en la demo."""
        return [usuario_json(u, es_asistente(u)) for u in contenedor.directorio.listar()]

    @app.get("/api/yo")
    def yo(usuario: Solicitante) -> dict[str, Any]:
        return {
            **usuario_json(usuario, es_asistente(usuario)),
            "ahora": contenedor.reloj.ahora().isoformat(),
            "avisos": [
                {"asunto": n.asunto, "mensaje": n.mensaje}
                for n in contenedor.notificador.de(usuario.id)[:10]
            ],
        }

    @app.get("/api/laboratorios")
    def laboratorios() -> list[dict[str, str]]:
        return [
            {"id": lab.id, "nombre": lab.nombre, "campus": lab.campus}
            for lab in consultas.laboratorios()
        ]

    # --- Horario (CU-07 y CU-08) --------------------------------------------------
    @app.get("/api/laboratorios/{laboratorio_id}/horario")
    def horario(laboratorio_id: str, fecha: date, usuario: Solicitante) -> dict[str, Any]:
        semana = SemanaISO.de(fecha)
        turnos = consultas.horario(usuario, laboratorio_id, semana)
        return {
            "semana": str(semana),
            "lunes": semana.lunes.isoformat(),
            "turnos": [turno_json(t, nombres) for t in turnos],
        }

    @app.get("/api/asistentes")
    def asistentes(fecha: date, usuario: Solicitante) -> list[dict[str, Any]]:
        return [carga_json(c) for c in consultas.asistentes_con_carga(usuario, SemanaISO.de(fecha))]

    @app.post("/api/turnos", status_code=201)
    def asignar_turno(entrada: AsignarTurnoEntrada, usuario: Solicitante) -> dict[str, Any]:
        resultado = contenedor.asignar_turno.ejecutar(
            AsignarTurnoComando(solicitante_id=usuario.id, **entrada.model_dump())
        )
        return {
            "turno_id": resultado.turno_id,
            "estado": resultado.estado.value,
            "requiere_aceptacion": resultado.requiere_aceptacion,
        }

    @app.get("/api/mis-turnos")
    def mis_turnos(usuario: Solicitante) -> list[dict[str, Any]]:
        hoy = contenedor.reloj.ahora().date()
        return [turno_json(t, nombres) for t in consultas.turnos_del_asistente(usuario.id, hoy)]

    @app.post("/api/turnos/{turno_id}/respuesta")
    def responder_turno(
        turno_id: str, entrada: RespuestaTurnoEntrada, usuario: Solicitante
    ) -> dict[str, str]:
        estado = contenedor.responder_turno.ejecutar(
            ResponderTurnoComando(usuario.id, turno_id, entrada.acepta)
        )
        return {"estado": estado.value}

    # --- Reservas (CU-15 y CU-16) -------------------------------------------------
    @app.get("/api/laboratorios/{laboratorio_id}/ocupacion")
    def ocupacion(laboratorio_id: str, fecha: date, usuario: Solicitante) -> dict[str, Any]:
        return ocupacion_json(consultas.ocupacion(laboratorio_id, fecha), usuario.id)

    @app.post("/api/reservas", status_code=201)
    def reservar(entrada: ReservarMaquinaEntrada, usuario: Solicitante) -> dict[str, Any]:
        resultado = contenedor.reservar_maquina.ejecutar(
            ReservarMaquinaComando(usuario.id, entrada.maquina_id, entrada.inicio, entrada.fin)
        )
        return {
            "reserva_id": resultado.reserva_id,
            "estado": resultado.estado.value,
            "limite_de_llegada": resultado.limite_de_llegada.isoformat(),
        }

    @app.get("/api/mis-reservas")
    def mis_reservas(usuario: Solicitante) -> list[dict[str, Any]]:
        hoy = contenedor.reloj.ahora().date()
        return [reserva_json(r) for r in consultas.reservas_del_estudiante(usuario.id, hoy)]

    # --- Cierre de mes (CU-19) ----------------------------------------------------
    @app.get("/api/cierres")
    def cierres(usuario: Solicitante) -> list[dict[str, Any]]:
        return [cierre_json(c, con_detalle=False) for c in consultas.cierres(usuario)]

    @app.post("/api/cierres", status_code=201)
    def cerrar_mes(entrada: CerrarMesEntrada, usuario: Solicitante) -> dict[str, Any]:
        resultado = contenedor.cerrar_mes.ejecutar(
            CerrarMesComando(usuario.id, entrada.anio, entrada.mes)
        )
        return {**cierre_json(resultado.cierre), "archivo": Path(resultado.archivo).name}

    @app.get("/api/cierres/{anio}/{mes}")
    def cierre(anio: int, mes: int, usuario: Solicitante) -> dict[str, Any]:
        encontrado = consultas.cierre(usuario, Mes(anio, mes))
        if encontrado is None:
            raise NoEncontrado(f"El mes {anio}-{mes:02d} no está cerrado.")
        return cierre_json(encontrado)

    @app.get("/api/cierres/{anio}/{mes}/archivo")
    def archivo_becas(anio: int, mes: int, usuario: Solicitante) -> Response:
        """El CSV se regenera desde el cierre guardado: el cierre es inmutable, así
        que el archivo siempre es el mismo, y cualquier réplica lo puede servir."""
        encontrado = consultas.cierre(usuario, Mes(anio, mes))
        if encontrado is None:
            raise NoEncontrado(f"El mes {anio}-{mes:02d} no está cerrado.")
        return Response(
            content=contenido_csv(encontrado),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{nombre_de_archivo(encontrado)}"'
            },
        )

    if CARPETA_WEB.is_dir():
        app.mount("/", StaticFiles(directory=CARPETA_WEB, html=True), name="web")
    return app


async def _liberar_periodicamente(contenedor: Contenedor) -> None:
    """Tarea de fondo: CU-16, liberar reservas sin presentarse (cada minuto)."""
    while True:
        try:
            liberadas = await asyncio.to_thread(contenedor.liberar_reservas.ejecutar)
            if liberadas:
                registro.info("Se liberaron %s reservas por ausencia.", liberadas)
        except Exception:  # la tarea no debe morir por un fallo puntual
            registro.exception("Falló la liberación periódica de reservas.")
        await asyncio.sleep(SEGUNDOS_ENTRE_LIBERACIONES)


def app_desde_entorno() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    return crear_app(contenedor_desde_entorno())
