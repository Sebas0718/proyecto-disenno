# 14. Descripción y justificación del diseño UX/UI

## 14.1 Usuarios y contexto de uso

| Usuario | Dispositivo y contexto | Lo que necesita de la pantalla |
|---------|------------------------|--------------------------------|
| Coordinador de laboratorio | Computadora, en su oficina, al inicio del semestre y cada semana | Ver la semana completa de un vistazo y asignar sin cometer errores |
| Coordinador de soporte | Computadora | Lo mismo, para todos los laboratorios, más el cierre de mes |
| Asistente | **Celular**, de pie en la puerta del laboratorio o entre clases | Responder un turno pendiente con un toque; ver sus próximos turnos |
| Estudiante | Celular o computadora | Saber si el laboratorio estará abierto y reservar sin sorpresas |

## 14.2 Pantallas

1. **Horario** (coordinadores, CU-07):
   - semana de lunes a domingo, con navegación anterior / hoy / siguiente;
   - formulario de asignación con **pistas en vivo**.
2. **Mis turnos** (asistente, CU-08): primero los pendientes, con botones Aceptar y Rechazar; abajo, los próximos turnos confirmados.
3. **Reservar máquina** (estudiantes, CU-15):
   - laboratorio y fecha;
   - franjas abiertas;
   - cuadrícula de máquinas con su ocupación;
   - formulario de hora y duración;
   - "Mis reservas".
4. **Cierre de mes** (coordinador de soporte, CU-19):
   - selección del mes;
   - confirmación;
   - tabla de liquidaciones con alertas;
   - historial y descarga del CSV.

Bocetos de las pantallas principales:

```
┌ Horario · Laboratorio 1 ─────────────── ‹ Anterior  Hoy  Siguiente › ┐
│ Lun 16    Mar 17    Mié 18    Jue 19    Vie 20    Sáb 21   Dom 22    │  ┌ Asignar turno ─────────┐
│ 08–11     08–12     08–11     08–12     08–11     Cerrado  Cerrado   │  │ Asistente [Pablo · 9/10h]│
│ Pablo     Marco     Pablo     Marco     Pablo                        │  │ Día [Viernes 20]         │
│ 13–15     13–15     13–15     13–15     13–15                        │  │ Inicio [15:00] Fin[17:00]│
│ Sofía     Sofía     Sofía     Sofía     Sofía                        │  │ ▓▓▓▓▓▓▓▓▓░ 11 de 10 h    │
└──────────────────────────────────────────────────────────────────────┘  │ ⚠ Superaría su tope      │
                                                                          │ [Asignar turno]          │
┌ Mis turnos (celular) ┐                                                  └──────────────────────────┘
│ Esperan su respuesta │
│ Sáb 21 · 11–12 LAB-3 │
│ [ Aceptar ][Rechazar]│
└──────────────────────┘
```

Las capturas reales se obtienen levantando el sistema (`docker compose up`) y abriendo,
por ejemplo, `http://localhost:8090/?usuario=CL-1&seccion=horario`.

## 14.3 Decisiones de diseño y su justificación

Las justificaciones se apoyan en las **10 heurísticas de usabilidad de Nielsen** y en
principios de accesibilidad (**WCAG 2.1**).

| Decisión | Heurística / principio | Por qué |
|----------|------------------------|---------|
| Pistas en vivo al asignar: horas usadas / tope con una barra, disponibilidad declarada ese día, advertencia "quedará pendiente" o "superaría su tope" | **Prevención de errores** (H5), **visibilidad del estado** (H1) | El problema de origen es que los topes se superaban "y se enteran un mes después". Aquí se ve *antes* de confirmar. |
| La duración de la reserva se elige de una lista (30 min a 2 h) | **Prevención de errores** (H5) | El error "más de 2 horas" no se puede cometer desde la pantalla. |
| Máquinas fuera de servicio o con el laboratorio cerrado aparecen **deshabilitadas** y con el motivo escrito | H5, **reconocer antes que recordar** (H6) | No se ofrece lo que no se puede usar. |
| Franjas "Abierto 08:00–11:00" visibles antes de reservar | H1, H6 | El estudiante sabe *antes* si el laboratorio estará abierto, que es el problema de "llegar y estar cerrado". |
| Mensajes de error con título en lenguaje del usuario ("Choca con otro turno del asistente") y detalle concreto del servidor ("ya tiene un turno en LAB-2 el 16/11 de 10:00 a 14:00") | **Ayudar a reconocer y recuperarse de errores** (H9), **lenguaje del mundo real** (H2) | Dice *qué* pasó y *qué* hacer, sin códigos técnicos. |
| Diálogo de confirmación para acciones irreversibles: cerrar el mes, rechazar un turno | **Control y libertad del usuario** (H3), H5 | "Un mes cerrado no se vuelve a calcular". El diálogo lo dice explícitamente. |
| Pestañas según el rol: un estudiante no ve "Cierre de mes" | **Diseño minimalista** (H8), H6 | Cada persona ve solo lo que puede usar. Igual, el servidor valida los permisos (AC-07). |
| Turno pendiente con borde punteado e insignia "Pendiente de aceptación" | **Consistencia** (H4), H1 | Los estados nunca se indican **solo con color**: siempre llevan texto (WCAG 1.4.1). |
| Mobile-first: una columna en el celular; la semana pasa de 7 columnas a una lista | **Flexibilidad** (H7), AC-06 | El asistente usa el celular de pie. |
| Botones y campos de al menos **44 × 44 px** | WCAG 2.5.5 (tamaño del objetivo) | Se tocan con el pulgar sin errores. |
| Etiquetas `<label>` en todos los campos, foco visible, enlace "Saltar al contenido", región `aria-live` para los mensajes, `role="alert"` en los errores | WCAG 1.3.1, 2.4.1, 2.4.7, 4.1.3 | La interfaz se puede usar con teclado y con lector de pantalla. |
| Contraste de texto de 4.5:1 o más y **modo oscuro** automático (`prefers-color-scheme`) | WCAG 1.4.3 | Legible en exteriores y de noche (turnos nocturnos). |
| Avisos (notificaciones) con contador en la barra superior | H1 | El asistente ve que tiene un turno pendiente; el coordinador ve que le rechazaron uno o que hubo horas sin pagar. |
| Términos del dominio en español y en el lenguaje del enunciado: "turno", "tope", "recargo", "liberar" | H2 | Es el vocabulario que usan los usuarios. |
| Montos con formato local (₡482 000,00) y números alineados a la derecha en la tabla del cierre | H2, H4 | Se comparan de un vistazo. |
| Filas de la tabla del cierre con horas no pagadas resaltadas, más un aviso arriba | H1 | "El coordinador de soporte tiene que saberlo." |
| Sin dependencias externas (ni CDN ni fuentes web) | Rendimiento percibido | La pantalla carga en conexiones lentas del campus. |

## 14.4 Sistema visual

- **Colores como variables** (`--primario`, `--exito`, `--aviso`, `--peligro`) con versión clara y oscura. Los significados son consistentes en todas las pantallas:
  - verde: confirmado o activo;
  - ámbar: pendiente o con alerta;
  - rojo: rechazado, cerrado o error.
- **Tipografía del sistema** (`system-ui`): es nativa en cada dispositivo y no hay que descargarla.
- **Tarjetas** para agrupar: la semana, el formulario, "Mis reservas".
- **Jerarquía:**
  - título de la pantalla;
  - subtítulo con el contexto (campus y semana);
  - contenido;
  - acción principal en color primario y una sola por formulario.

## 14.5 Validación pendiente con usuarios

El prototipo no se probó con usuarios reales. Se recomienda una prueba rápida con 3 a
5 asistentes. La tarea sería: "responda su turno pendiente desde el celular". La
métrica es el tiempo, con meta de menos de 10 s (AC-06), más los errores cometidos.
