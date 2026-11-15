# ADR-0004 · Reglas críticas también como restricciones de la base (defensa en profundidad)

- **Estado:** aceptada

## Contexto
Las reglas viven en el dominio. Sin embargo, dos peticiones simultáneas pueden pasar
las dos la verificación en Python antes de que cualquiera guarde. Es una condición de
carrera: el clásico "verificar y luego actuar".

## Decisión
Se repiten como restricciones de PostgreSQL las invariantes cuya violación sería grave:

| Invariante | Restricción |
|------------|-------------|
| Un asistente no tiene turnos traslapados | `EXCLUDE USING gist (asistente_id WITH =, tsrange(inicio, fin) WITH &&) WHERE estado <> 'RECHAZADO'` |
| Un laboratorio tiene un solo responsable a la vez | `EXCLUDE ... (laboratorio_id WITH =, tsrange WITH &&)` |
| Una máquina no se reserva dos veces | `EXCLUDE ... (maquina_id WITH =, tsrange WITH &&) WHERE estado IN ('ACTIVA','EN_USO')` |
| Una reserva dura 2 h como máximo | `CHECK (fin - inicio <= interval '2 hours')` |
| Los tarifarios no se traslapan | `EXCLUDE ... (daterange(desde, hasta, '[]') WITH &&)` |
| Un mes se cierra una sola vez | `PRIMARY KEY (anio, mes)` |
| Un mes cerrado no se modifica | Trigger `BEFORE UPDATE OR DELETE` que lanza un error |

El repositorio traduce cada violación al **mismo error de dominio** (`E-TRASLAPE`,
`E-MAQUINA-OCUPADA`…), así que el caso de uso y la pantalla no distinguen quién la
detectó.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| Solo en el dominio | No resiste la concurrencia. |
| Solo en la base | Los mensajes serían pobres, las reglas no se podrían probar sin la base y la lógica quedaría dispersa en SQL. |
| Aislamiento SERIALIZABLE en todo | Resuelve la carrera, pero produce reintentos frecuentes y no protege si alguien escribe por fuera de la aplicación. |

## Consecuencias
- **A favor:** la medida de AC-05 se cumple ("0 traslapes en la base en cualquier momento").
- **En contra:** algunas reglas quedan en dos lugares. Se mitiga con pruebas de integración que verifican ambas (`tests/integracion/test_postgres.py`).
- **No cubierto:** el **tope semanal** es una suma y no se puede expresar como `EXCLUDE`. Se protege con el bloqueo del asistente (ADR-0005).
