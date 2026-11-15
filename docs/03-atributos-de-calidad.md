# 3. Atributos de calidad

Cada atributo se expresa como un **escenario de calidad**, para que se pueda medir y no
quede en una frase vaga como "debe ser rápido". Un escenario tiene seis partes:

- **Fuente:** quién o qué provoca el estímulo.
- **Estímulo:** lo que ocurre.
- **Artefacto:** la parte del sistema afectada.
- **Entorno:** las condiciones en que ocurre.
- **Respuesta:** lo que hace el sistema.
- **Medida:** cómo se comprueba que la respuesta es suficiente.

Las **tácticas** son las decisiones de diseño con que se logra cada respuesta.

## Prioridades

| Prioridad | Atributo | Por qué |
|-----------|----------|---------|
| Alta | Integridad de las reglas (AC-05) | Es el problema que origina el proyecto: tope superado, horas mal reportadas |
| Alta | Disponibilidad y aislamiento de carga (AC-02, AC-03) | Lo pide el enunciado de forma explícita |
| Alta | Modificabilidad de tarifas (AC-04) | "se los cambian casi cada semestre y casi nunca con tiempo" |
| Media | Rendimiento (AC-01) | "responder siempre de manera rápida" |
| Media | Usabilidad móvil (AC-06) | El asistente marca de pie en la puerta, con el celular |
| Media | Seguridad y autorización (AC-07) | Cada coordinador solo puede tocar su laboratorio |
| Alta (para el equipo) | Testabilidad (AC-08) | Lo exige el núcleo ejecutable: pruebas con dobles y funciones de aptitud |

## Escenarios

### AC-01 Rendimiento
| Parte | Valor |
|---|---|
| Fuente | 200 estudiantes al mismo tiempo, en la semana de exámenes |
| Estímulo | Consultan la ocupación y reservan una máquina |
| Artefacto | API y base de datos |
| Entorno | Operación normal, en el pico del semestre |
| Respuesta | La reserva se confirma o se rechaza con el motivo |
| Medida | p95 < 500 ms y p99 < 1 s, sin errores 5xx |

**Tácticas:**
- Las consultas usan índices, por ejemplo `turno_por_asistente` y `reserva_por_estudiante`.
- Las reglas se evalúan en memoria con los datos de **una semana**; nunca se recorre todo el historial.
- La API no guarda estado entre peticiones, así que se pueden agregar réplicas.
- La mejora prevista es un *pool* de conexiones.

### AC-02 Disponibilidad
| Parte | Valor |
|---|---|
| Fuente | Falla de hardware o un proceso que se cae |
| Estímulo | Se cae una réplica de la API o el nodo primario de la base de datos |
| Artefacto | Sistema completo |
| Entorno | Durante el semestre lectivo |
| Respuesta | El tráfico pasa a las réplicas sanas; la base promueve la réplica de respaldo |
| Medida | 99,5 % de disponibilidad mensual; recuperación en menos de 1 minuto para la API y menos de 5 minutos para la base, sin perder cierres confirmados |

**Tácticas:**
- Hay redundancia activa: 2 o más réplicas de la API detrás de un balanceador.
- Cada réplica tiene un *health check* (`/api/salud`) y se reinicia sola si falla (`restart: unless-stopped`).
- PostgreSQL usa replicación en *streaming* con un nodo de respaldo.
- Las tareas periódicas son idempotentes y pueden correr en cualquier réplica.

Detalle en [05-arquitectura.md](05-arquitectura.md#despliegue) y en el [ADR-0015](adr/0015-alta-disponibilidad.md).

### AC-03 Aislamiento de carga
| Parte | Valor |
|---|---|
| Fuente | La matrícula de la institución |
| Estímulo | Carga 10 veces mayor sobre la infraestructura compartida del TEC |
| Artefacto | Despliegue de CompuLab |
| Entorno | Semana de matrícula o de finales |
| Respuesta | CompuLab no se degrada |
| Medida | La latencia p95 de CompuLab no varía más de un 20 % frente a una semana normal |

**Tácticas:**
- Los contenedores y la base de datos son **propios**, con límites de CPU y memoria reservados, y no se comparten con matrícula.
- No hay dependencias en línea con otros sistemas: el directorio solo se consulta al iniciar sesión y Becas recibe un archivo una vez al mes.

### AC-04 Modificabilidad (tarifas y reglas de pago)
| Parte | Valor |
|---|---|
| Fuente | La Coordinación de Soporte |
| Estímulo | Cambia las tarifas o el porcentaje de recargo una semana antes del cierre |
| Artefacto | Datos del tarifario |
| Entorno | En producción |
| Respuesta | Se registra un tarifario nuevo con su vigencia, sin programar ni desplegar |
| Medida | 0 líneas de código cambiadas; el cambio está listo en menos de 5 minutos |

**Tácticas:**
- Las tarifas son **datos con vigencia** (ADR-0006).
- La *regla* de cuándo aplica el recargo es una **estrategia** (`PoliticaDeRecargo`): cambiarla toca una sola clase.
- El formato del archivo está detrás del puerto `ExportadorPlanilla`.

### AC-05 Integridad de las reglas bajo concurrencia
| Parte | Valor |
|---|---|
| Fuente | Dos coordinadores de laboratorios distintos |
| Estímulo | Asignan al mismo asistente, al mismo tiempo, turnos que juntos se traslapan o pasan su tope |
| Artefacto | Caso de uso CU-07 y base de datos |
| Entorno | Operación normal |
| Respuesta | Uno se registra y el otro se rechaza con el motivo |
| Medida | 0 traslapes y 0 asignaciones sobre el tope en la base de datos, en cualquier momento |

**Tácticas:**
- Defensa en profundidad (ADR-0004): las reglas están en el dominio **y** en restricciones `EXCLUDE` de PostgreSQL.
- El asistente se bloquea con `SELECT … FOR UPDATE` mientras dura la asignación (ADR-0005).
- La unidad de trabajo es transaccional.

### AC-06 Usabilidad móvil
| Parte | Valor |
|---|---|
| Fuente | Un asistente |
| Estímulo | Llega a la puerta del laboratorio y quiere marcar entrada, o responder un turno pendiente |
| Artefacto | Pantallas web |
| Entorno | Celular, de pie y con prisa |
| Respuesta | Lo hace en una sola pantalla y con un toque |
| Medida | En menos de 10 segundos; botones de al menos 44 × 44 px; sin desplazamiento horizontal a 360 px de ancho |

**Tácticas:**
- Diseño *mobile-first*.
- Botones grandes.
- Una columna en el celular.

Detalle en [14-ux-ui.md](14-ux-ui.md).

### AC-07 Seguridad y autorización
| Parte | Valor |
|---|---|
| Fuente | Un coordinador de laboratorio |
| Estímulo | Intenta ver o modificar el horario de otro laboratorio, aunque sea llamando a la API directamente |
| Artefacto | Casos de uso y consultas |
| Entorno | Operación normal |
| Respuesta | Se rechaza con `E-NO-AUTORIZADO` (HTTP 403) |
| Medida | El 100 % de las operaciones verifica el permiso **en el servidor**, con pruebas automáticas |

**Tácticas:**
- La autorización vive en el dominio (`Usuario.puede_administrar_horario`) y se verifica en el caso de uso, nunca solo en la pantalla.
- La identidad la da el directorio institucional.

### AC-08 Testabilidad
| Parte | Valor |
|---|---|
| Fuente | Un desarrollador del equipo |
| Estímulo | Cambia una regla del negocio |
| Artefacto | Dominio y aplicación |
| Entorno | En su máquina, sin Docker |
| Respuesta | Corre las pruebas y sabe si rompió algo |
| Medida | Más de 150 pruebas en menos de 5 s, sin base de datos ni red; el build falla si se rompe la regla de dependencia |

**Tácticas:**
- Arquitectura hexagonal con puertos inyectados.
- Dobles de prueba: un reloj fijo y espías del notificador y del exportador.
- Repositorios en memoria transaccionales.
- Funciones de aptitud FF-1 y FF-2 (ADR-0014).
