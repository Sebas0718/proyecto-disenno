# 1. Requerimientos, contexto y alcance

## 1.1 Contexto

La Escuela de Computación tiene **cuatro laboratorios en dos campus**. No los atiende
personal administrativo sino **asistentes estudiantiles**: estudiantes con beca de
asistencia que trabajan por turnos y cobran por hora.

Hoy todo se lleva a mano:

| Hoy | Problema que produce |
|-----|----------------------|
| El horario vive en una hoja de cálculo compartida | Hay turnos sin cubrir que nadie nota hasta que el laboratorio abre tarde |
| Los cambios de turno se acuerdan por mensajería | El coordinador no los registra, y las horas reportadas no son las trabajadas |
| Nadie controla el tope de horas | Un asistente pasa su tope y se entera un mes después, cuando Becas rechaza el reporte |
| Las máquinas se ocupan por orden de llegada | Un estudiante llega y no hay máquina libre, o el laboratorio está cerrado |

La Escuela quiere un sistema que ordene cuatro cosas: **reclutamiento, horario, uso de
máquinas y pago**.

## 1.2 Actores e interesados

| Actor | Qué hace en el sistema | Qué ve |
|-------|------------------------|--------|
| **Coordinador de soporte** | Abre la convocatoria, entrevista, admite (categoría y tope) o rechaza, da de baja, fija tarifas, **cierra el mes** y resuelve excepciones | Todos los laboratorios |
| **Coordinador de laboratorio** | Arma el horario de **su** laboratorio, aprueba o rechaza cambios de turno y revisa turnos sin cubrir | Solo su laboratorio |
| **Asistente** | Declara su disponibilidad, acepta turnos fuera de ella, ofrece y toma turnos, marca entrada y salida | Sus turnos y los de su laboratorio |
| **Estudiante** | Reserva una máquina y la usa | Las máquinas y los horarios abiertos |
| Directorio institucional (Centro de Cómputo) | Sistema externo: dice quién es quién al entrar | — |
| Oficina de Becas | Sistema externo: fija el tope semanal fuera del sistema y recibe cada mes el archivo de pago | — |

Un asistente **también es estudiante**, así que puede reservar máquinas.

## 1.3 Alcance

**Dentro** (se diseña todo; se implementan de punta a punta los marcados con ★):

- Reclutamiento: convocatoria, postulación con disponibilidad, entrevista y resolución.
- Horario: ★ asignar turno con sus reglas, ★ aceptar o rechazar un turno fuera de la disponibilidad, ofertas y cambios de turno, marcas de entrada y salida, y consulta de turnos sin asignar o no cubiertos.
- Máquinas: ★ reservar, ★ liberar por ausencia a los 15 minutos, marcar fuera de servicio o reparada, y el reporte de uso.
- Pago: ★ cerrar el mes, calcular el pago y generar el archivo para Becas, además de configurar las tarifas.

**Fuera** (lo dice el enunciado):

- La asignación de becas y sus requisitos. El sistema *recibe* la categoría y el tope.
- El pago propiamente dicho. Solo se hace el cálculo.
- El inventario de hardware, más allá de qué máquinas hay y si están en servicio.

## 1.4 Requerimientos funcionales

| ID | Requerimiento | Fuente en el enunciado | CU |
|----|---------------|------------------------|----|
| RF-01 | Abrir la convocatoria de asistentes de cada semestre | "cada semestre la Coordinación de Soporte abre una convocatoria" | CU-01 |
| RF-02 | Postularse indicando bloques horarios y laboratorios | "se postula indicando en qué bloques…" | CU-02 |
| RF-03 | Registrar la entrevista: quién la hizo, cuándo y con qué resultado | "queda registrado quién la hizo, cuándo y con qué resultado" | CU-03 |
| RF-04 | Admitir con categoría y tope semanal, o rechazar; un rechazado puede volver a postularse | "puede admitir… o puede rechazarlo" | CU-04 |
| RF-05 | Corregir el tope semanal de un asistente | "puede corregirlo después si Becas se lo cambia" | CU-05 |
| RF-06 | Renuncia o baja: sus turnos futuros quedan sin cubrir y se avisa a tiempo | "sus turnos que todavía no han ocurrido quedan sin cubrir" | CU-06 |
| RF-07 | Asignar un turno (laboratorio, día, inicio, fin y exactamente un responsable) | "Un turno es un laboratorio, un día…" | **CU-07** |
| RF-08 | No permitir traslapes de un asistente, aunque sean en otro laboratorio o campus | "La primera es que a nadie se le asigne un turno que se traslape…" | **CU-07** |
| RF-09 | No superar en ninguna semana el tope de horas | "La segunda es que nadie supere…" | **CU-07** |
| RF-10 | No asignar un bloque no declarado, salvo que el asistente lo acepte | "La tercera…" | **CU-07, CU-08** |
| RF-11 | No asignar turnos a un asistente inactivo | "A un asistente que ya no está activo no se le puede asignar…" | **CU-07** |
| RF-12 | El coordinador de laboratorio solo modifica su laboratorio; el de soporte, todos | "solo arma y modifica el horario de su laboratorio" | **CU-07** |
| RF-13 | Ofrecer un turno, tomarlo y aprobar el cambio, con verificación de traslape y tope | "lo ofrece a otros estudiantes…" | CU-09 a CU-11 |
| RF-14 | La oferta vence 24 h antes del turno; quien ofrece la puede retirar | "Una oferta que nadie tomó vence…" | CU-12 |
| RF-15 | Marcar entrada y salida desde el celular; se paga lo trabajado de verdad | "marca entrada cuando llega y salida cuando se va" | CU-13 |
| RF-16 | Un turno que termina sin entrada queda no cubierto y se avisa al coordinador | "queda como no cubierto y el coordinador… tiene que enterarse" | CU-13, CU-14 |
| RF-17 | Consultar por semana los turnos sin asignar y los no cubiertos | "El coordinador puede consultar, para cualquier semana…" | CU-14 |
| RF-18 | Reservar una máquina solo en una franja con turno, máximo 2 h, una activa a la vez y 6 h por semana | "las reglas que la Coordinación de Soporte quiere…" | **CU-15** |
| RF-19 | Liberar una reserva si no se presenta en 15 minutos | "si no se presenta dentro de los primeros quince minutos…" | **CU-16** |
| RF-20 | Si un turno se cae, avisar a quienes reservaron en esa franja | "si el turno se cae… hay que avisarle a quien reservó" | CU-14, CU-17 |
| RF-21 | Marcar una máquina fuera de servicio (cancela reservas futuras y avisa) o reparada | "El asistente de turno puede marcar una máquina como fuera de servicio" | CU-17 |
| RF-22 | Reporte por laboratorio y semana de máquinas fuera de servicio y uso | "Al coordinador de soporte le interesa poder ver…" | CU-18 |
| RF-23 | Cerrar el mes: consolidar las horas reales, aplicar tarifa y recargo, y dejar sin pagar lo que pasa del tope | "El primer día de cada mes se cierra el mes anterior" | **CU-19** |
| RF-24 | Generar el archivo que acepta Becas | "El resultado del cierre se le entrega a Planilla" | **CU-19** |
| RF-25 | Un mes cerrado no se recalcula ni se corrige | "Un mes cerrado no se vuelve a calcular ni se corrige" | **CU-19** |
| RF-26 | Configurar las tarifas por categoría y el porcentaje de recargo, que cambian casi cada semestre | "se los cambian casi cada semestre y casi nunca con tiempo" | CU-20 |
| RF-27 | Identificar a cada persona con el directorio institucional | "es el que dice quién es quién cuando alguien entra" | CU-21 |

## 1.5 Requerimientos no funcionales

| ID | Requerimiento | Detalle en |
|----|---------------|-----------|
| RNF-01 | **Rendimiento**: responder siempre rápido | [03](03-atributos-de-calidad.md) · AC-01 |
| RNF-02 | **Disponibilidad**: alta disponibilidad durante el semestre | AC-02 |
| RNF-03 | **Aislamiento de carga**: la matrícula y los finales no deben afectarlo | AC-03 |
| RNF-04 | **Modificabilidad**: cambiar tarifas y recargo sin programar | AC-04 |
| RNF-05 | **Integridad**: nunca dos turnos traslapados ni una máquina reservada dos veces, ni con concurrencia | AC-05 |
| RNF-06 | **Usabilidad móvil**: marcar entrada y salida de pie en la puerta, con el celular | AC-06 |
| RNF-07 | **Seguridad**: cada rol ve y modifica solo lo que le corresponde | AC-07 |
| RNF-08 | **Testabilidad**: las reglas se prueban sin base de datos ni red | AC-08 |
| RNF-09 | **Restricciones**: contenedores Linux, PostgreSQL 14 y solo código abierto | [04](04-restricciones.md) |

## 1.6 Supuestos e interpretaciones

El enunciado deja huecos. Estas decisiones se tomaron con el equipo y cada una tiene su ADR:

| # | Pregunta abierta | Decisión | ADR |
|---|------------------|----------|-----|
| I-1 | ¿Qué es "una semana" para el tope? | Semana ISO, de lunes a domingo | [0007](adr/0007-semana-iso-y-semanas-partidas.md) |
| I-2 | Si una semana queda partida entre dos meses, ¿cómo se cuenta el tope? | Con la semana completa; cada hora se paga en el mes en que se trabajó | 0007 |
| I-3 | Un turno nocturno **y** de fin de semana, ¿lleva el recargo dos veces? | No, se aplica **una sola vez** | [0008](adr/0008-interpretaciones-de-reglas.md) |
| I-4 | ¿El recargo se aplica a las horas después de las 18:00 o al turno completo? | Al turno completo si **empieza** a las 18:00 o después (lectura literal) | 0008 |
| I-5 | ¿Cuáles horas sobre el tope quedan sin pagar? | Las **últimas** en orden cronológico | 0008 |
| I-6 | ¿Cómo "acepta" el asistente un bloque no declarado? | El turno queda **pendiente de aceptación** y él lo acepta o rechaza | 0008 |
| I-7 | ¿Pueden dos asistentes tener turno a la vez en un laboratorio? | No: "exactamente una persona responsable" | 0008 |
| I-8 | ¿Qué es una reserva "activa"? | Una que no se canceló ni se liberó y que todavía no termina | [0010](adr/0010-reglas-de-reserva.md) |
| I-9 | ¿Qué cuenta para las 6 h semanales? | Todas, menos las canceladas; las liberadas por ausencia sí cuentan | 0010 |
| I-10 | ¿Qué formato acepta Becas? | CSV en UTF-8, una fila por asistente (hay que confirmarlo con Becas) | [0012](adr/0012-archivo-becas-csv.md) |
| I-11 | ¿Zona horaria? | Hora local de Costa Rica, sin cambio de horario | [0009](adr/0009-hora-local.md) |
| I-12 | ¿Qué turno "abre" el laboratorio para reservar? | Solo uno **confirmado**; uno pendiente no garantiza que haya asistente | 0010 |
| I-13 | Si Becas cambia el tope a mitad de mes, ¿cuál se usa al cerrar? | El tope vigente al cerrar (simplificación documentada; el historial de topes es una mejora) | 0007 |
