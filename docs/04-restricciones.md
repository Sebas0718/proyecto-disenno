# 4. Restricciones tecnológicas

Las restricciones **no se negocian** (las puso la Escuela). Se distinguen de las
decisiones, que sí tomó el equipo y están en los ADR.

| ID | Restricción | Fuente | Cómo se cumple |
|----|-------------|--------|----------------|
| R-01 | Se despliega en la infraestructura del TEC: **contenedores Linux** | Enunciado | `Dockerfile` (python:3.12-slim) y `docker-compose.yml` |
| R-02 | Base de datos **PostgreSQL 14** | Enunciado | Imagen `postgres:14`; el esquema solo usa funciones disponibles en la 14 (`EXCLUDE USING gist`, `btree_gist`, `tsrange`, `daterange`) |
| R-03 | Sin nube externa | Enunciado | Todo corre en contenedores propios; no hay servicios administrados de terceros |
| R-04 | Sin licencias: **solo código abierto** | Enunciado | Ver la tabla de licencias |
| R-05 | El front end no tiene que conectarse a la base de datos | Entregable B | Las pantallas hablan solo con la API (HTTP/JSON) |
| R-06 | Dependencias externas declaradas como interfaces (Protocol o clase abstracta) e inyectadas | Entregable B | `src/compulab/aplicacion/puertos.py` (Protocol) y la raíz de composición |
| R-07 | Ningún acceso real a red, archivos o reloj dentro del dominio | Entregable B | Verificado por la función de aptitud FF-2 |
| R-08 | Pruebas con dobles, no con base de datos | Entregable B | `tests/dobles.py`; las pruebas de integración están separadas (`-m integracion`) |
| R-09 | README de 10 líneas o menos para instalar y probar | Entregable B | `README.md` |
| R-10 | Equipo de 3 personas, entrega el 30 de noviembre | Curso | Alcance de implementación limitado a 3 casos de uso (más 2 de apoyo) |

## Software utilizado y sus licencias

| Componente | Uso | Licencia |
|------------|-----|----------|
| Python 3.12+ | Lenguaje | PSF (abierta) |
| FastAPI / Starlette | API HTTP | MIT / BSD-3 |
| Uvicorn | Servidor ASGI | BSD-3 |
| Pydantic | Validación del formato de entrada | MIT |
| psycopg 3 | Controlador de PostgreSQL | LGPL-3 |
| tzdata | Zonas horarias | Apache-2.0 |
| PostgreSQL 14 (+ btree_gist) | Base de datos | PostgreSQL (tipo MIT) |
| pytest, import-linter, ruff, httpx2 | Pruebas y calidad (solo en desarrollo) | MIT / BSD-2 |
| uv | Gestor de dependencias | MIT / Apache-2.0 |
| Docker Engine / Compose | Contenedores | Apache-2.0 |
| HTML, CSS, JavaScript | Pantallas, sin frameworks ni CDN | — |
