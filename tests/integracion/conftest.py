"""Pruebas de integración contra PostgreSQL 14 real.

Requieren la base levantada (``docker compose up -d db``). Cada ejecución crea
un esquema temporal (``prueba_xxxxxx``), aplica 001_esquema.sql ahí y lo borra
al terminar: no tocan los datos de la demo.
"""

import os
import uuid
from pathlib import Path

import psycopg
import pytest

from compulab.infraestructura.postgres import fabrica_postgres

URL = os.environ.get(
    "COMPULAB_DB_URL_PRUEBAS", "postgresql://compulab:compulab@localhost:5440/compulab"
)
ESQUEMA_SQL = Path(__file__).resolve().parents[2] / "db" / "migraciones" / "001_esquema.sql"


@pytest.fixture
def fabrica():
    esquema = f"prueba_{uuid.uuid4().hex[:8]}"
    try:
        administracion = psycopg.connect(URL, autocommit=True)
    except psycopg.OperationalError as error:
        pytest.fail(
            f"No hay PostgreSQL en {URL}. Levántelo con `docker compose up -d db`.\n{error}"
        )
    with administracion:
        administracion.execute(f"CREATE SCHEMA {esquema}")
        administracion.execute(f"SET search_path TO {esquema}, public")
        administracion.execute(ESQUEMA_SQL.read_text(encoding="utf-8"))
        try:
            yield fabrica_postgres(URL, options=f"-c search_path={esquema},public")
        finally:
            administracion.execute(f"DROP SCHEMA {esquema} CASCADE")
