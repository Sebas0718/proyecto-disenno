# ADR-0014 · Funciones de aptitud: import-linter (FF-1) y verificador AST (FF-2)

- **Estado:** aceptada

## Contexto
Se piden "al menos dos [funciones de aptitud] que verifiquen una propiedad del diseño
[...] y que fallen el build. Cada una con su prueba que le planta una violación a
propósito y exige que la encuentre."

Una **función de aptitud** (*fitness function*) es una prueba automática que no
verifica comportamiento sino una **propiedad de la arquitectura**.

## Decisión
| | FF-1 Regla de dependencia | FF-2 Dominio puro |
|-|---------------------------|-------------------|
| Propiedad | Las importaciones van solo `api → infraestructura → aplicacion → dominio` | El dominio no toca red, archivos, base de datos, frameworks, reloj ni azar |
| Herramienta | import-linter, contrato `layers` en `pyproject.toml` | Verificador propio con `ast` (`tests/aptitud/pureza.py`) |
| Prueba sobre el código real | `test_el_codigo_respeta_la_regla_de_dependencia` | `test_el_dominio_real_es_puro` |
| Violación plantada | Un paquete `plantado` con el **mismo contrato**, donde el dominio importa la aplicación y la aplicación importa la infraestructura | Archivos temporales con `import socket`, `datetime.now()`, `open()`… |
| Cómo falla el build | `uv run pytest`, o el paso `lint-imports` en CI | `uv run pytest` |

FF-2 usa el **árbol sintáctico** y no una búsqueda de texto. Así, un comentario o un
texto que diga "datetime.now()" no cuenta como violación (lo cubre
`test_no_confunde_texto_ni_horas_con_llamadas_al_reloj`).

## Alternativas consideradas
- Buscar con `grep` en CI. Da falsos positivos con comentarios y no detecta `import x as y`.
- Hacer las dos con import-linter. No detecta *llamadas* a `datetime.now()`, porque `datetime` sí es un import permitido.

## Consecuencias
Quedó comprobado: al plantar una violación real en `src/compulab/dominio/`, ambas
pruebas fallaron.
