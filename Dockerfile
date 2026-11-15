# Imagen de la API de CompuLab (contenedor Linux, ADR-0002).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    TZ=America/Costa_Rica

WORKDIR /app

# Primero solo las dependencias (capa que se reutiliza mientras no cambie uv.lock).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY web ./web
RUN uv sync --frozen --no-dev

# No correr como root dentro del contenedor.
RUN useradd --create-home compulab && mkdir -p /datos/archivos && chown compulab /datos/archivos
USER compulab

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/salud')"

CMD ["uvicorn", "compulab.api.app:app_desde_entorno", "--factory", "--host", "0.0.0.0", "--port", "8000"]
