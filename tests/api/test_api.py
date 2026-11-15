"""Pruebas del adaptador HTTP: traducción de peticiones y de errores de dominio.

Usan la app real con adaptadores en memoria y reloj fijo (sin base de datos).
"""

import pytest
from fastapi.testclient import TestClient

from compulab.api.app import crear_app
from compulab.api.composicion import construir_contenedor
from tests.dobles import Escenario, asistente, dia, en, tarifario


@pytest.fixture
def cliente(tmp_path) -> TestClient:
    esc = Escenario()
    esc.con_asistente(asistente("A1", tope=10))
    esc.con_turno(en(dia(0), 8, 12), asistente_id="A1")
    esc.con_tarifario(tarifario())
    contenedor = construir_contenedor(esc.fabrica, esc.reloj, tmp_path, esc.directorio)
    return TestClient(crear_app(contenedor, liberar_en_segundo_plano=False))


def como(usuario: str) -> dict[str, str]:
    return {"X-Usuario-Id": usuario}


TURNO = {
    "laboratorio_id": "LAB-1",
    "asistente_id": "A1",
    "dia": dia(1).isoformat(),
    "hora_inicio": "08:00",
    "hora_fin": "10:00",
}


def test_sin_identificarse_responde_401(cliente):
    assert cliente.post("/api/turnos", json=TURNO).status_code == 401


def test_asignar_turno_responde_201_con_el_estado(cliente):
    respuesta = cliente.post("/api/turnos", json=TURNO, headers=como("CL1"))
    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "CONFIRMADO"


def test_una_regla_violada_responde_409_con_su_codigo(cliente):
    datos = {**TURNO, "dia": dia(0).isoformat(), "hora_inicio": "11:00", "hora_fin": "13:00"}
    respuesta = cliente.post("/api/turnos", json=datos, headers=como("CL1"))
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "E-TRASLAPE"


def test_sin_permiso_responde_403(cliente):
    respuesta = cliente.post("/api/turnos", json=TURNO, headers=como("CL2"))
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "E-NO-AUTORIZADO"


def test_dato_invalido_responde_422(cliente):
    datos = {**TURNO, "hora_inicio": "10:00", "hora_fin": "09:00"}
    respuesta = cliente.post("/api/turnos", json=datos, headers=como("CL1"))
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "E-INTERVALO-INVALIDO"


def test_reservar_y_ver_la_ocupacion(cliente):
    reserva = {
        "maquina_id": "M-LAB-1-1",
        "inicio": f"{dia(0).isoformat()}T09:00",
        "fin": f"{dia(0).isoformat()}T11:00",
    }
    assert cliente.post("/api/reservas", json=reserva, headers=como("E1")).status_code == 201
    ocupacion = cliente.get(
        "/api/laboratorios/LAB-1/ocupacion",
        params={"fecha": dia(0).isoformat()},
        headers=como("E1"),
    ).json()
    maquina = next(m for m in ocupacion["maquinas"] if m["id"] == "M-LAB-1-1")
    assert maquina["reservas"][0]["propia"] is True
    assert len(ocupacion["franjas_abiertas"]) == 1


def test_cerrar_mes_y_descargar_el_csv(cliente):
    respuesta = cliente.post("/api/cierres", json={"anio": 2026, "mes": 10}, headers=como("SOP"))
    assert respuesta.status_code == 201
    archivo = cliente.get("/api/cierres/2026/10/archivo", headers=como("SOP"))
    assert archivo.status_code == 200
    assert archivo.headers["content-type"].startswith("text/csv")
    assert "becas-2026-10.csv" in archivo.headers["content-disposition"]
    assert archivo.text.startswith("anio,mes,asistente_id")


def test_un_coordinador_de_laboratorio_no_ve_el_horario_de_otro(cliente):
    respuesta = cliente.get(
        "/api/laboratorios/LAB-2/horario", params={"fecha": dia(0).isoformat()}, headers=como("CL1")
    )
    assert respuesta.status_code == 403
