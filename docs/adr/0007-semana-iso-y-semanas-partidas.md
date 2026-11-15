# ADR-0007 · Semana ISO y semanas partidas entre meses

- **Estado:** aceptada

## Contexto
El tope de Becas es **semanal**, pero el cierre es **mensual**. El enunciado no dice
qué día empieza la semana ni qué pasa con una semana que queda partida entre dos meses.

## Decisión
1. La semana es **ISO 8601: de lunes a domingo** (`SemanaISO`).
2. Para cerrar un mes se leen las asistencias desde el **lunes de la semana del día 1** hasta el fin del mes (`periodo_de_calculo`).
3. Las horas del mes anterior en esa semana **cuentan para el tope**, pero no se pagan otra vez porque ya se pagaron en su mes.
4. Cada hora se paga en el mes **en que se trabajó**.
5. Se usa el **tope vigente al momento de cerrar**. Guardar el historial de topes es una mejora documentada.

## Ejemplo
- La semana del 28/09 al 04/10/2026 queda partida entre septiembre y octubre.
- Con tope de 10 h, Ana trabaja 8 h el martes 29/09 y 4 h el jueves 01/10.
- Al cerrar octubre, de las 4 h del 01/10 solo 2 caben en el tope y las otras 2 quedan sin pagar.
- Lo prueba `test_pc4_las_horas_del_mes_anterior_en_la_misma_semana_cuentan_para_el_tope`.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| Semana de domingo a sábado | Es menos estándar. La semana ISO es la que usa la biblioteca estándar de Python (`isocalendar`). |
| Cortar la semana en el borde del mes | Permitiría trabajar el tope completo dos veces en una misma semana real, y Becas lo rechazaría. |

## Consecuencias
- **A favor:** el tope se respeta igual que lo verifica Becas, que trabaja por semanas.
- **En contra:** el cierre lee hasta 6 días del mes anterior. Es un costo insignificante.
