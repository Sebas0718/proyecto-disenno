# ADR-0008 · Interpretaciones de reglas ambiguas del enunciado

- **Estado:** aceptada (decididas con el equipo el 2026-11-13; la I-7 la propuso el diseñador y está pendiente de que el equipo la confirme)

| # | Texto del enunciado | Interpretación | Dónde vive |
|---|---------------------|----------------|------------|
| I-3 | "Las horas de turnos que empiezan a las seis de la tarde o después, y las de sábado y domingo, se pagan con un recargo." | El recargo se aplica **una sola vez** aunque se cumplan las dos condiciones: un sábado a las 19:00 paga tarifa × 1,5 y no × 2,25. | `RecargoNocturnoOFinDeSemana` |
| I-4 | Ídem | Lleva recargo **todo** el turno que *empieza* a las 18:00 o después, y no solo la parte posterior a las 18:00. Se mira el **inicio programado** del turno, no la hora en que llegó el asistente. | `Asistencia.inicio_programado` |
| I-5 | "Las horas trabajadas por encima del tope semanal no se pagan" | Se paga en **orden cronológico** hasta el tope; las **últimas** horas de la semana quedan sin pagar. | `LiquidadorMensual.liquidar` |
| I-6 | "...salvo que el propio asistente lo acepte" | El turno se crea **PENDIENTE_ACEPTACION**, se avisa al asistente y él lo acepta o lo rechaza. Mientras está pendiente, ocupa su tiempo y cuenta para su tope, pero **no abre** el laboratorio. | `PoliticaDeAsignacion.asignar`, `Turno` |
| I-7 | "exactamente una persona responsable: no existen [...] turnos compartidos entre dos" | Un laboratorio no puede tener dos turnos que se traslapen. | `UnResponsablePorLaboratorio` y la restricción `turno_un_responsable_por_laboratorio` |

## Alternativas descartadas
- **I-3:** acumular los recargos sumando o multiplicando.
- **I-5:** dejar sin pagar las horas más baratas o las más caras. Introduce un sesgo y es más difícil de explicar a Becas.
- **I-6:** una casilla "el asistente aceptó" que marca el coordinador. Es más simple, pero el sistema no comprobaría la aceptación.
- **I-7:** permitir dos asistentes a la vez. Contradice "exactamente una persona responsable".

## Consecuencias
Cada interpretación tiene pruebas con nombre propio, para cambiarla con seguridad si
el profesor o la Coordinación la aclaran de otra forma. Por ejemplo, la I-7 se elimina
quitando una regla de la lista `REGLAS_DE_ASIGNACION` y la restricción SQL.
