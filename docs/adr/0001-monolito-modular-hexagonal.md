# ADR-0001 · Monolito modular con arquitectura hexagonal

- **Estado:** aceptada
- **Fecha:** 2026-11-13

## Contexto
El enunciado pide:
- regla de dependencia entre capas;
- dependencias externas como interfaces inyectadas;
- ningún acceso a red, archivos o reloj dentro del dominio;
- pruebas con dobles.

El sistema atiende 4 laboratorios y unos cientos de personas. Lo construye un equipo
de 3 estudiantes en tres semanas.

## Decisión
Un **monolito modular** con **arquitectura hexagonal**:
- un solo desplegable;
- módulos por tema (horario, reservas, pagos);
- capas `dominio ← aplicacion ← infraestructura/api`;
- puertos declarados con `typing.Protocol`.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| Microservicios (uno por módulo) | Agregan llamadas por red, varios despliegues, consistencia eventual y monitoreo distribuido. La carga y el equipo no lo justifican. |
| Capas clásicas (presentación → negocio → datos) | La capa de negocio dependería de la de datos, así que las reglas no se podrían probar sin la base. Además invierte la regla que pide el enunciado. |
| "Script transaccional" (la lógica en los endpoints) | Es rápido de escribir, pero produce un modelo anémico y reglas duplicadas, y el enunciado prohíbe el modelo anémico. |

## Consecuencias
- **A favor:**
  - las reglas se prueban en milisegundos;
  - cambiar PostgreSQL, el formato del CSV o el notificador toca una sola clase;
  - la regla de dependencia se puede verificar automáticamente (FF-1).
- **En contra:**
  - hay más archivos e indirección (puertos, adaptadores, raíz de composición) que en un CRUD simple;
  - hay que mapear entre filas y objetos a mano.
