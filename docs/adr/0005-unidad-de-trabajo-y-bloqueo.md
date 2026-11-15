# ADR-0005 · Unidad de trabajo transaccional y bloqueo pesimista del asistente

- **Estado:** aceptada

## Contexto
Un caso de uso lee y escribe varios repositorios. Todo debe quedar guardado o nada.
Por ejemplo, si falla el archivo de Becas, el mes no puede quedar cerrado a medias.

Además, el tope semanal se calcula sumando turnos. Dos asignaciones simultáneas en
laboratorios distintos podrían pasar cada una la verificación y, juntas, superar el tope.

## Decisión
1. **Unidad de trabajo** (`UnidadDeTrabajo`, en `puertos.py`):
   - agrupa los repositorios bajo una transacción;
   - `confirmar()` hace commit;
   - salir del bloque `with` sin confirmar hace rollback.
2. Al asignar un turno, el asistente se lee con `obtener(id, bloquear=True)`, que en PostgreSQL es `SELECT … FOR UPDATE`. Una segunda asignación al mismo asistente **espera** a que termine la primera, y entonces ve su turno.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| Bloqueo optimista (columna `version`) | Obliga a reintentar en el caso de uso. El bloqueo pesimista es más simple de explicar, y la espera dura milisegundos porque las transacciones son cortas. |
| Repositorios que hacen commit cada uno | No hay atomicidad entre pasos. |

## Consecuencias
- **A favor:**
  - atomicidad (probada con `test_ext_7a_si_falla_el_archivo_el_mes_no_queda_cerrado`);
  - el tope se respeta bajo concurrencia.
- **En contra:** dos asignaciones al **mismo** asistente se hacen en serie. Con 1–2 coordinadores por laboratorio es irrelevante.
