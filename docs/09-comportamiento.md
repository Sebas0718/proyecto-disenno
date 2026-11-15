# 9. Comportamiento

Hay dos tipos de diagrama en esta sección:

- **Diagramas de secuencia:** muestran *quién llama a quién* en cada caso de uso implementado.
- **Diagramas de estado:** muestran *cómo cambia* cada entidad.

## 9.1 Secuencia · CU-07 Asignar turno

```mermaid
sequenceDiagram
    autonumber
    actor C as Coordinador
    participant W as Pantalla horario.js
    participant A as API /api/turnos
    participant U as AsignarTurno
    participant D as DirectorioInstitucional
    participant T as UnidadDeTrabajo
    participant P as PoliticaDeAsignacion
    participant N as Notificador

    C->>W: elige asistente, día, horas
    W-->>C: pistas: horas/tope y disponibilidad (prevención)
    C->>W: Asignar turno
    W->>A: POST {laboratorio, asistente, día, inicio, fin}
    A->>U: ejecutar(AsignarTurnoComando)
    U->>D: buscar(solicitante)
    U->>T: with fabrica() (abre transacción)
    U->>T: laboratorios.obtener(lab)
    U->>U: solicitante.puede_administrar_horario(lab)?
    U->>U: IntervaloTiempo.en_dia(...)  (inv: fin > inicio)
    U->>T: asistentes.obtener(id, bloquear=True)  (SELECT … FOR UPDATE)
    U->>T: turnos.del_asistente_en(semana) / del_laboratorio_en(franja)
    U->>P: asignar(id, coordinador, solicitud)
    loop cada regla
        P->>P: futuro · activo · sin traslape · un responsable · tope
    end
    P->>P: declaro_disponible? → CONFIRMADO : PENDIENTE
    P-->>U: Turno
    U->>T: turnos.agregar(turno)  (EXCLUDE en PostgreSQL)
    U->>T: confirmar()  (COMMIT)
    opt PENDIENTE_ACEPTACION
        U->>N: notificar(asistente, "Turno pendiente…")
    end
    U-->>A: TurnoAsignado(id, estado)
    A-->>W: 201 {turno_id, estado}
    W-->>C: "Turno asignado" / "Enviado para aceptación"
    Note over U,A: Si una regla falla: ErrorDeDominio → ROLLBACK → 409/403/404/422 {codigo, mensaje}
```

## 9.2 Secuencia · CU-15 Reservar máquina (y CU-16)

```mermaid
sequenceDiagram
    autonumber
    actor E as Estudiante
    participant W as reservas.js
    participant A as API /api/reservas
    participant U as ReservarMaquina
    participant T as UnidadDeTrabajo
    participant R as Reserva
    participant P as PoliticaDeReserva

    E->>W: elige laboratorio y fecha
    W->>A: GET ocupacion (franjas abiertas + máquinas)
    E->>W: elige máquina, hora y duración (máx. 2 h en la lista)
    W->>A: POST {maquina, inicio, fin}
    A->>U: ejecutar(comando)
    U->>U: estudiante.puede_reservar()?
    U->>T: maquinas.obtener(id)
    U->>R: Reserva(...)  (inv: ≤ 2 h, mismo día)
    U->>T: turnos.del_laboratorio_en · reservas.de_maquina_en · activas_del_estudiante · del_estudiante_en(semana)
    U->>P: verificar(SolicitudDeReserva)
    P->>P: en servicio · futura · laboratorio abierto (cubren) · máquina libre · 1 activa · ≤ 6 h
    U->>T: reservas.agregar(r)  (EXCLUDE máquina)
    U->>T: confirmar()
    U-->>A: ReservaRegistrada(id, ACTIVA, limite = inicio + 15 min)
    A-->>W: 201
    W-->>E: "Preséntese antes de las HH:MM"

    Note over A,T: Cada minuto (tarea de fondo, CU-16)
    A->>U: LiberarReservasNoPresentadas.ejecutar()
    U->>T: reservas.sin_presentarse(ahora)
    U->>R: liberar_por_ausencia(ahora)  (ACTIVA → LIBERADA)
    U->>T: actualizar(r) · confirmar()
```

## 9.3 Secuencia · CU-19 Cerrar el mes

```mermaid
sequenceDiagram
    autonumber
    actor S as Coord. soporte
    participant W as cierre.js
    participant A as API /api/cierres
    participant U as CerrarMes
    participant T as UnidadDeTrabajo
    participant L as LiquidadorMensual
    participant X as ExportadorPlanilla
    participant N as Notificador

    S->>W: elige mes y confirma (diálogo "es irreversible")
    W->>A: POST {anio, mes}
    A->>U: ejecutar(CerrarMesComando)
    U->>U: puede_cerrar_mes()? · mes.termino_en(ahora)?
    U->>T: cierres.existe(mes)?  → E-MES-YA-CERRADO
    U->>T: tarifarios.todos() → CatalogoDeTarifas
    U->>T: asistencias.en(lunes de la semana del día 1 … fin de mes)
    loop por asistente con horas en el mes
        U->>T: asistentes.obtener(id)
        U->>L: liquidar(mes, asistente, asistencias, tarifas)
        L->>L: orden cronológico · tope por semana ISO · recargo · tarifa vigente
        L-->>U: LiquidacionAsistente
    end
    U->>U: CierreMensual(mes, ahora, liquidaciones)
    U->>T: cierres.agregar(c)  (PK anio, mes)
    U->>X: exportar(c) → "becas-AAAA-MM.csv"
    U->>T: confirmar()  (si X falla: ROLLBACK, el mes NO queda cerrado)
    opt hay horas no pagadas
        U->>N: notificar(coordinador de soporte, detalle)
    end
    U-->>A: MesCerrado(cierre, archivo)
    A-->>W: 201 {liquidaciones, total}
    W-->>S: tabla + aviso de horas no pagadas + botón CSV
```

## 9.4 Actividad · cálculo de una liquidación

```mermaid
flowchart TD
    A[Asistencias del asistente desde el lunes de la semana del día 1] --> B[Ordenar por hora de entrada]
    B --> C{¿Quedan asistencias?}
    C -- no --> Z[Redondear monto a céntimos → LiquidacionAsistente]
    C -- sí --> D[semana = SemanaISO de la fecha]
    D --> E["pagables = min(trabajados, tope − usados[semana])"]
    E --> F["usados[semana] += trabajados"]
    F --> G{¿La fecha es del mes que se cierra?}
    G -- no, es del mes anterior --> C
    G -- sí --> H[tarifario = vigente en la fecha]
    H --> I{¿Turno empieza ≥ 18:00 o es sábado/domingo?}
    I -- sí --> J["con_recargo += pagables<br/>monto += tarifa × horas × (1 + %)"]
    I -- no --> K["base += pagables<br/>monto += tarifa × horas"]
    J & K --> L["no_pagados += trabajados − pagables"]
    L --> C
```

## 9.5 Estados · Turno

```mermaid
stateDiagram-v2
    [*] --> CONFIRMADO: asignar() dentro de la disponibilidad
    [*] --> PENDIENTE_ACEPTACION: asignar() fuera de la disponibilidad
    PENDIENTE_ACEPTACION --> CONFIRMADO: aceptar() [solo el asistente]
    PENDIENTE_ACEPTACION --> RECHAZADO: rechazar() [solo el asistente] / avisar al coordinador
    RECHAZADO --> [*]
    CONFIRMADO --> SIN_ASIGNAR: asistente renuncia o es dado de baja (CU-06, diseño)
    CONFIRMADO --> NO_CUBIERTO: termina sin marca de entrada (CU-13, diseño)
    CONFIRMADO --> CUBIERTO: hubo entrada y salida (CU-13, diseño)
```

Implementados: PENDIENTE_ACEPTACION, CONFIRMADO y RECHAZADO. Los demás estados
pertenecen a casos de uso diseñados pero no programados.

## 9.6 Estados · Reserva

```mermaid
stateDiagram-v2
    [*] --> ACTIVA: reservar()
    ACTIVA --> EN_USO: registrar_llegada(ahora) [inicio ≤ ahora < inicio + 15 min]
    ACTIVA --> LIBERADA: liberar_por_ausencia(ahora) [ahora ≥ inicio + 15 min]
    ACTIVA --> CANCELADA: cancelar() · máquina fuera de servicio · turno caído
    EN_USO --> [*]: termina la franja
    LIBERADA --> [*]
    CANCELADA --> [*]
```

## 9.7 Estados · Asistente, Máquina y Oferta de turno

```mermaid
stateDiagram-v2
    state Asistente {
      [*] --> ACTIVO: admitir (CU-04)
      ACTIVO --> RENUNCIO: renunciar()
      ACTIVO --> DADO_DE_BAJA: dar_de_baja()
    }
    state Maquina {
      [*] --> EN_SERVICIO
      EN_SERVICIO --> FUERA_DE_SERVICIO: marcar_fuera_de_servicio() / cancelar reservas futuras
      FUERA_DE_SERVICIO --> EN_SERVICIO: marcar_reparada()
    }
    state OfertaDeTurno {
      [*] --> PUBLICADA: ofrecer (CU-09)
      PUBLICADA --> TOMADA: tomar (CU-10, el primero)
      PUBLICADA --> RETIRADA: retirar (quien ofreció)
      PUBLICADA --> VENCIDA: 24 h antes del turno
      TOMADA --> APROBADA: aprobar [sin traslape y dentro del tope]
      TOMADA --> RECHAZADA: rechazar (sin razón)
    }
```

La `OfertaDeTurno` está diseñada pero no implementada. Al aprobarla se **reutiliza**
la `PoliticaDeAsignacion` con las reglas `SinTraslapes` y `DentroDelTopeSemanal`
(ver [10-patrones.md](10-patrones.md)).
