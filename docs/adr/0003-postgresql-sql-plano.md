# ADR-0003 · PostgreSQL 14 con SQL plano (sin ORM)

- **Estado:** aceptada

## Contexto
PostgreSQL 14 es obligatorio. Hay que traducir objetos del dominio con atributos
privados e invariantes en el constructor.

## Decisión
- Los repositorios escriben **SQL plano** con **psycopg 3**.
- Mapean filas a objetos del dominio con funciones pequeñas (`_turno(fila)`, `_reserva(fila)`).
- El esquema vive en `db/migraciones/001_esquema.sql`.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| SQLAlchemy ORM (mapeo declarativo) | Obliga a que las clases del dominio hereden del ORM o lo conozcan, y eso rompe la regla de dependencia. El mapeo "imperativo" lo evita, pero agrega una capa que habría que aprender y defender. |
| SQLAlchemy Core | Es razonable. Se descartó por simplicidad: hay pocas consultas y son legibles en SQL. |
| Alembic para migraciones | Sobra con un solo archivo de esquema. Queda como mejora (05-arquitectura §5.6). |

## Consecuencias
- **A favor:**
  - cada consulta se lee y se puede explicar;
  - se aprovechan funciones propias de PostgreSQL (`EXCLUDE`, `tsrange`) sin pelear con un ORM;
  - el dominio no sabe que existe una base de datos.
- **En contra:**
  - el mapeo es manual;
  - cambiar el esquema requiere tocar el SQL y el mapeo.
