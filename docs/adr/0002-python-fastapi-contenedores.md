# ADR-0002 · Python 3.12 + FastAPI en contenedores Linux

- **Estado:** aceptada

## Contexto
El sistema debe correr en contenedores Linux del TEC con software libre. El enunciado
menciona "Protocol o clase abstracta", que es vocabulario de Python. El equipo
conoce Python.

## Decisión
- **Python 3.12 o superior.** Se usa `typing.Protocol` para los puertos.
- **FastAPI** para la API HTTP, servida con Uvicorn.
- Imagen `python:3.12-slim`, con dependencias fijadas en `uv.lock`, y el proceso corre como usuario no root.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| Java + Spring Boot | Es sólida y tiene ArchUnit, pero es más verbosa y el equipo la domina menos. |
| Node/TypeScript + NestJS | Se aleja de la pista del enunciado (Protocol). El tipado del dominio es menos estricto en tiempo de ejecución. |
| Flask o Django | Flask no valida la entrada por sí solo. Django empuja hacia su ORM y su modelo de capas, que va en contra de ADR-0001 y ADR-0003. |

## Consecuencias
- **A favor:**
  - FastAPI valida el formato de entrada con tipos y genera la documentación OpenAPI en `/docs`;
  - `uv` hace que la instalación sea reproducible.
- **En contra:**
  - Python es más lento que Java o Go. Para esta carga no importa (AC-01 se cumple con holgura).
