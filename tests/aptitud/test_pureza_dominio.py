"""Función de aptitud FF-2: el dominio no toca red, archivos ni reloj.

Igual que FF-1: corre sobre el código real (debe estar limpio) y sobre código
plantado con violaciones a propósito (debe encontrarlas todas).
"""

from pathlib import Path

import pytest

from tests.aptitud.pureza import buscar_violaciones

DOMINIO = Path(__file__).resolve().parents[2] / "src" / "compulab" / "dominio"


def test_el_dominio_real_es_puro():
    violaciones = buscar_violaciones(DOMINIO)
    assert violaciones == [], "\n".join(map(str, violaciones))


def test_el_verificador_si_revisa_archivos_del_dominio():
    assert len(list(DOMINIO.rglob("*.py"))) > 10


@pytest.mark.parametrize(
    ("codigo", "esperado"),
    [
        ("import socket\n", "socket"),
        ("from pathlib import Path\n", "pathlib"),
        ("import psycopg\n", "psycopg"),
        ("import urllib.request\n", "urllib.request"),
        ("import time\n", "import prohibido en el dominio: time"),
        ("from datetime import datetime\nx = datetime.now()\n", "datetime.now()"),
        ("import datetime\nx = datetime.date.today()\n", "date.today()"),
        ("datos = open('planilla.csv').read()\n", "open()"),
    ],
)
def test_detecta_violaciones_plantadas(tmp_path, codigo, esperado):
    (tmp_path / "modulo_plantado.py").write_text(codigo)
    violaciones = buscar_violaciones(tmp_path)
    assert len(violaciones) == 1
    assert esperado in violaciones[0].detalle
    assert violaciones[0].linea >= 1


def test_no_confunde_texto_ni_horas_con_llamadas_al_reloj(tmp_path):
    (tmp_path / "limpio.py").write_text(
        "from datetime import datetime, time\n"
        "# datetime.now() en un comentario no cuenta\n"
        'MENSAJE = "no use datetime.now()"\n'
        "CORTE = time(18, 0)\n"
        "def f(ahora: datetime) -> bool:\n"
        "    return ahora.time() >= CORTE\n"
    )
    assert buscar_violaciones(tmp_path) == []
