# CompuLab · Administración de laboratorios
Requisitos: Docker y [uv](https://docs.astral.sh/uv/) (uv es opcional: ver paso 7). Documento de diseño: [docs/README.md](docs/README.md).
1. Instalar dependencias: `uv sync`
2. Pruebas (dominio, casos de uso, API y funciones de aptitud; sin base de datos): `uv run pytest`
3. Regla de dependencia entre capas: `uv run lint-imports`
4. Levantar PostgreSQL 14 + API + pantallas: `docker compose up --build -d` → http://localhost:8090
5. Pruebas de integración contra PostgreSQL (con el paso 4 arriba): `uv run pytest -m integracion`
6. Sin Docker, con datos en memoria: `uv run uvicorn compulab.api.app:app_desde_entorno --factory` → http://localhost:8000
7. Solo con Docker, sin uv (estilo, capas, pruebas e integración, como el CI): `docker compose run --rm pruebas`
