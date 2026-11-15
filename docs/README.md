# Documento de diseño · CompuLab

Administración de los laboratorios de cómputo de la Escuela de Computación:
reclutamiento de asistentes, horario, uso de las máquinas y cálculo del pago.

Este documento es el **entregable A**. El **entregable B** (núcleo ejecutable) está en
`src/`, `web/`, `db/` y `tests/`, y se instala siguiendo el `README.md` de la raíz.

## Índice (en el orden que pide el enunciado)

| # | Sección | Archivo |
|---|---------|---------|
| 1 | Requerimientos, contexto y alcance | [01-requerimientos.md](01-requerimientos.md) |
| 2 | Casos de uso (y contratos de operación) | [02-casos-de-uso.md](02-casos-de-uso.md) |
| 3 | Atributos de calidad | [03-atributos-de-calidad.md](03-atributos-de-calidad.md) |
| 4 | Restricciones tecnológicas | [04-restricciones.md](04-restricciones.md) |
| 5 | Arquitectura | [05-arquitectura.md](05-arquitectura.md) |
| 6 | Decisiones (ADR) | [06-adr.md](06-adr.md) y la carpeta [adr/](adr/) |
| 7 | Componentes | [07-componentes.md](07-componentes.md) |
| 8 | Clases | [08-clases.md](08-clases.md) |
| 9 | Comportamiento | [09-comportamiento.md](09-comportamiento.md) |
| 10 | Patrones | [10-patrones.md](10-patrones.md) |
| 11 | Trazabilidad | [11-trazabilidad.md](11-trazabilidad.md) |
| 12 | Evaluación grupal | [12-evaluacion-grupal.md](12-evaluacion-grupal.md) (plantilla) |
| 13 | Bitácora individual | [13-bitacora-individual.md](13-bitacora-individual.md) (plantilla) |
| 14 | Descripción y justificación del diseño UX/UI | [14-ux-ui.md](14-ux-ui.md) |
| 15 | Diseño de la base de datos | [15-diseno-bd.md](15-diseno-bd.md) |

## Cómo leerlo

- Los diagramas están escritos en **Mermaid** (texto). GitHub, GitLab y VS Code
  los dibujan solos. Para entregar en PDF:
  `pandoc docs/*.md -o diseno.pdf` (con el filtro `mermaid-filter`), o bien
  exportar desde VS Code con la extensión *Markdown PDF*.
- Los identificadores se repiten en todo el documento y en el código, para
  que la trazabilidad sea directa:
  - `RF-xx` y `RNF-xx` son los requerimientos.
  - `CU-xx` son los casos de uso, y `CO-xx` los contratos.
  - `E-...` son los códigos de error, en `src/compulab/dominio/comun/errores.py`.
  - `ADR-00xx` son las decisiones.
  - `FF-x` son las funciones de aptitud.
- Lo que el enunciado no decía y hubo que decidir está marcado como
  **Interpretación** y tiene su ADR.

## Resumen en cinco líneas

1. **Arquitectura.** Es un monolito modular con arquitectura hexagonal: el dominio en el centro y los adaptadores (PostgreSQL, HTTP, CSV, reloj) alrededor, inyectados por interfaces.
2. **Reglas.** Las reglas del negocio viven en clases del dominio con invariantes en el constructor y atributos privados. Las más críticas se repiten como restricciones de PostgreSQL.
3. **Casos de uso implementados.** Son tres de punta a punta, desde la pantalla hasta la base de datos: *asignar turno*, *reservar máquina* y *cerrar el mes* (con el CSV para Becas).
4. **Pruebas.** Hay una prueba por cada poscondición y por cada extensión, con dobles de prueba. Dos funciones de aptitud hacen fallar el build si se rompe la arquitectura.
5. **Despliegue.** Se despliega en contenedores Linux con PostgreSQL 14 y solo software libre. El diseño de producción tiene réplicas sin estado para alta disponibilidad.
