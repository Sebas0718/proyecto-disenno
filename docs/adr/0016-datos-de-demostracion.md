# ADR-0016 · Datos de demostración relativos a hoy, cargados con los repositorios

- **Estado:** aceptada

## Contexto
La demo se presentará en una fecha desconocida. Si los datos tuvieran fechas fijas, a
la semana siguiente no habría turnos futuros para reservar.

## Decisión
`infraestructura/datos_demo.py` genera los datos a partir de **hoy**:
- turnos desde la semana del día 1 del mes anterior hasta la próxima semana;
- asistencias reales del mes anterior, con casos interesantes:
  - una hora de más por encima del tope;
  - un turno no cubierto;
  - turnos nocturnos y de fin de semana;
- un turno pendiente de aceptación.

Se cargan **con los mismos repositorios** del sistema, tanto en memoria como en
PostgreSQL, así que hay una sola fuente de verdad para los datos de ejemplo.

## Consecuencias
- **A favor:** la demo siempre tiene sentido, y cargarla también prueba los repositorios.
- **En contra:** las cifras exactas del cierre cambian según el mes en que se presente. Las pruebas automáticas usan datos fijos.
