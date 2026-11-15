# 10. Patrones

Para cada patrón: **qué problema resuelve aquí**, **dónde está** en el código y
**qué cuesta**. Un patrón solo vale si resuelve un problema real del sistema.

## 10.1 Patrones de arquitectura

### Puertos y adaptadores (arquitectura hexagonal)
- **Problema:** las reglas no deben depender de PostgreSQL, FastAPI ni del reloj. Así se pueden probar con dobles y cambiar la tecnología.
- **Dónde:**
  - los puertos están en `aplicacion/puertos.py`;
  - los adaptadores, en `infraestructura/` y `api/`.
- **Costo:** más archivos e indirección. Ver el [ADR-0001](adr/0001-monolito-modular-hexagonal.md).

### Raíz de composición (inyección de dependencias manual)
- **Problema:** alguien tiene que decidir qué implementación concreta recibe cada caso de uso, y esa decisión no debe estar repartida por el código.
- **Dónde:** `api/composicion.py`. Es el **único** archivo que crea adaptadores concretos; los casos de uso los reciben por el constructor.
- **Por qué sin framework de inyección:** se arma con unas 20 líneas visibles, y un framework sería un concepto más que defender.

### CQRS simplificado (comandos separados de consultas)
- **Problema:** las pantallas necesitan lecturas variadas (horario, ocupación, cierres) que no tienen reglas. Mezclarlas con los casos de uso los ensuciaría.
- **Dónde:**
  - comandos en `aplicacion/casos_uso/`, que pasan por el dominio y confirman;
  - consultas en `aplicacion/consultas.py`, que solo leen y nunca confirman.
- **Costo:** dos lugares donde buscar. No hay bases de datos separadas, así que no hay consistencia eventual.

## 10.2 Patrones de diseño (GoF y DDD)

### Specification / cadena de reglas
- **Problema:** las reglas de asignación y de reserva deben verificarse **en orden**, cada una con su propio error. Además, algunas se reutilizan: al aprobar un cambio de turno hay que "verificar otra vez lo mismo".
- **Dónde:**
  - el protocolo `ReglaDeAsignacion` lo implementan `TurnoDebeSerFuturo`, `AsistenteDebeEstarActivo`, `SinTraslapes`, `UnResponsablePorLaboratorio` y `DentroDelTopeSemanal`;
  - `ReglaDeReserva` sigue la misma idea, con seis reglas;
  - `PoliticaDeAsignacion` y `PoliticaDeReserva` las recorren.
- **Beneficio:**
  - agregar una regla es una clase nueva, sin tocar las demás (principio abierto/cerrado);
  - para aprobar un cambio de turno basta `PoliticaDeAsignacion(reglas=(SinTraslapes(), DentroDelTopeSemanal()))`;
  - la regla I-7 (un responsable por laboratorio) se agregó así.
- **Costo:** una clase pequeña por regla.

### Strategy
- **Problema:** la **regla** del recargo (nocturno o fin de semana) la fija la Coordinación y podría cambiar, por ejemplo para incluir feriados.
- **Dónde:** el protocolo `PoliticaDeRecargo` lo implementa `RecargoNocturnoOFinDeSemana`, y se inyecta en `LiquidadorMensual`.
- **Diferencia con los datos:** el **porcentaje** es un dato del `Tarifario` (ADR-0006); la **regla** de cuándo aplica es la estrategia.

### State (con enumeración)
- **Problema:** `Turno` y `Reserva` tienen ciclos de vida con transiciones prohibidas: aceptar un turno ya rechazado, o liberar una reserva en uso.
- **Dónde:** `EstadoTurno` y `EstadoReserva`, con métodos que validan la transición (`aceptar()`, `liberar_por_ausencia()`) y lanzan `E-TRANSICION-INVALIDA`. Los diagramas están en [09-comportamiento.md](09-comportamiento.md).
- **Por qué un enum y no una clase por estado (State clásico):** hay pocas transiciones y cada estado tiene poco comportamiento. Una clase por estado sería más código sin más claridad. Si crecieran, se migra.

### Repository
- **Problema:** el dominio necesita "los turnos del asistente en la semana" sin saber de SQL.
- **Dónde:** los 8 protocolos `Repositorio*`, con dos implementaciones cada uno (PostgreSQL y memoria).
- **Detalle:** el repositorio da el **siguiente id** (`siguiente_id()`), así el dominio no genera identificadores al azar.

### Unit of Work
- **Problema:** varias escrituras deben confirmarse juntas o no hacerse. Por ejemplo, cerrar el mes y generar el archivo.
- **Dónde:** el protocolo `UnidadDeTrabajo`, implementado por `UnidadDeTrabajoPostgres` (transacción) y `UnidadDeTrabajoEnMemoria` (copia y reemplazo).
- **Prueba:** `test_ext_7a_si_falla_el_archivo_el_mes_no_queda_cerrado`.

### Value Object (DDD)
- **Problema:** conceptos como "un tramo de tiempo" o "un monto" tienen reglas (fin > inicio, nunca float) que se repetirían en todos lados.
- **Dónde:** `IntervaloTiempo`, `SemanaISO`, `Mes`, `Dinero`, `BloqueDisponible`, `LiquidacionAsistente`. Son inmutables y se comparan por valor.

### Servicio de dominio (DDD)
- **Problema:** algunas reglas involucran varios objetos y no pertenecen a ninguno. El tope semanal mira todos los turnos del asistente; el pago mira asistencias, tarifas y recargo.
- **Dónde:** `PoliticaDeAsignacion`, `PoliticaDeReserva` y `LiquidadorMensual`. Son puros: reciben todo como parámetro.

### Factory
- **Problema:** el estado inicial de un turno depende de una regla (la disponibilidad), y un `Turno` nunca debe nacer en un estado inconsistente.
- **Dónde:** `PoliticaDeAsignacion.asignar()` y los constructores alternativos `IntervaloTiempo.en_dia()`, `SemanaISO.de()` y `Mes.de()`.

### Adapter
- **Dónde:**
  - `ExportadorCsvBecas` adapta un `CierreMensual` al formato que entiende Becas;
  - los repositorios Postgres adaptan filas a objetos y traducen las violaciones de restricciones a errores de dominio;
  - `app.py` adapta los errores de dominio a HTTP.

### Test doubles (Meszaros)
- **Dónde:** `tests/dobles.py`:
  - `RelojFijo` es un *stub*;
  - `NotificadorEspia` y `ExportadorEspia` son *spies*;
  - `UnidadDeTrabajoEnMemoria` es un *fake*.

  Cumplen el requisito "pruebas con dobles, no con base de datos".

## 10.3 Principios que guían el diseño

| Principio | Dónde se nota |
|-----------|---------------|
| **SRP** (responsabilidad única) | Cada regla es una clase; cada caso de uso, una operación; cada adaptador, una tecnología |
| **OCP** (abierto/cerrado) | Nuevas reglas, estrategias de recargo o formatos de exportación sin modificar lo existente |
| **LSP** | Cualquier `UnidadDeTrabajo` (Postgres o memoria) sirve a los casos de uso. Las pruebas de integración corren el mismo caso de uso sobre PostgreSQL |
| **ISP** | Puertos pequeños (`Reloj` tiene un solo método) en lugar de un "servicio de infraestructura" gigante |
| **DIP** (inversión de dependencias) | La aplicación define las interfaces; la infraestructura depende de ellas, y no al revés (verificado por FF-1) |
| **Tell, don't ask** | `turno.aceptar()` en lugar de `turno.estado = CONFIRMADO` |
| **Fail fast** | Invariantes en el constructor: nunca existe un objeto inválido |

## 10.4 Antipatrones evitados

- **Modelo anémico:** las reglas están en el dominio y no en "servicios" con getters y setters.
- **Smart UI:** la pantalla **anticipa** errores, pero **nunca decide**. El servidor verifica todo (AC-07).
- **Reloj escondido:** ningún `datetime.now()` en el dominio (FF-2). La hora siempre se inyecta.
- **Float para dinero:** `Dinero` rechaza `float`.
