# 8. Clases

## 8.1 Convenciones del modelo de dominio

- **Entidades.** Tienen identidad propia (`id`) y estado que cambia: `Asistente`, `Turno`, `Reserva`, `Maquina`, `Tarifario`, `Asistencia`, `CierreMensual` y `Usuario`.
  - Sus **atributos son privados** (`self._estado`) y se leen con propiedades de solo lectura.
  - El estado **solo cambia con métodos que verifican la regla**: `turno.aceptar()`, `reserva.liberar_por_ausencia(ahora)`.
  - Dos entidades son iguales si tienen el mismo `id`.
- **Objetos de valor.** No tienen identidad y son inmutables: `IntervaloTiempo`, `SemanaISO`, `Mes`, `Dinero`, `BloqueDisponible`, `LiquidacionAsistente`.
  - Son `@dataclass(frozen=True)`: cualquier intento de asignar un atributo lanza `FrozenInstanceError`.
- **Invariantes en el constructor.** Ningún objeto inválido llega a existir. Si los datos rompen una regla, el constructor lanza un `ErrorDeDominio`.
- **Sin modelo anémico.** Las clases con reglas tienen comportamiento, no solo datos. Un modelo anémico son clases con getters y setters y la lógica en "servicios". Solo `Laboratorio` es un contenedor de datos simple, porque no tiene reglas.

## 8.2 Dominio: común

```mermaid
classDiagram
    class IntervaloTiempo {
      <<value object>>
      +inicio: datetime
      +fin: datetime
      +en_dia(dia, hora_inicio, hora_fin)$ IntervaloTiempo
      +duracion: timedelta
      +minutos: int
      +semana: SemanaISO
      +se_traslapa_con(otro) bool
      +contiene(otro) bool
    }
    note for IntervaloTiempo "inv: fin > inicio; sin zona horaria"
    class SemanaISO {
      <<value object>>
      +anio: int
      +numero: int
      +de(fecha)$ SemanaISO
      +lunes: date
      +intervalo: IntervaloTiempo
    }
    class Mes {
      <<value object>>
      +anio: int
      +numero: int
      +primer_dia: date
      +siguiente() Mes
      +contiene(fecha) bool
      +termino_en(ahora) bool
    }
    class Dinero {
      <<value object>>
      +monto: Decimal
      +cero()$ Dinero
      +__add__(otro) Dinero
      +por(factor) Dinero
      +redondeado() Dinero
    }
    note for Dinero "inv: Decimal (no float), >= 0"
    class Rol {
      <<enumeration>>
      ESTUDIANTE
      COORDINADOR_LABORATORIO
      COORDINADOR_SOPORTE
    }
    class Usuario {
      -_id: str
      -_nombre: str
      -_rol: Rol
      -_laboratorio_id: str?
      +puede_administrar_horario(lab) bool
      +puede_reservar() bool
      +puede_cerrar_mes() bool
    }
    note for Usuario "inv: coord. de laboratorio tiene exactamente 1 lab; los demás ninguno"
    class ErrorDeDominio {
      +codigo: str
      +mensaje: str
    }
    ErrorDeDominio <|-- NoAutorizado
    ErrorDeDominio <|-- NoEncontrado
    ErrorDeDominio <|-- DatoInvalido
    ErrorDeDominio <|-- ReglaDeNegocioViolada
    Usuario --> Rol
    IntervaloTiempo ..> SemanaISO
```

`cubren(intervalos, objetivo)` es una función del módulo `tiempo`. Responde si un
conjunto de intervalos cubre otro **sin huecos**. Se usa para saber si un laboratorio
está abierto toda una reserva y si un turno está dentro de la disponibilidad.

## 8.3 Dominio: horario

```mermaid
classDiagram
    class Categoria {
      <<enumeration>>
      A
      B
    }
    class EstadoAsistente {
      <<enumeration>>
      ACTIVO
      RENUNCIO
      DADO_DE_BAJA
    }
    class BloqueDisponible {
      <<value object>>
      +dia: DiaSemana
      +hora_inicio: time
      +hora_fin: time
    }
    class Disponibilidad {
      -_bloques: tuple
      +incluye(intervalo) bool
    }
    class Asistente {
      -_id
      -_nombre
      -_categoria: Categoria
      -_tope: Decimal
      -_disponibilidad: Disponibilidad
      -_estado: EstadoAsistente
      +esta_activo: bool
      +tope_minutos_semanales: int
      +declaro_disponible(intervalo) bool
      +corregir_tope(nuevo)
      +renunciar()
      +dar_de_baja()
    }
    note for Asistente "inv: 0 < tope <= 168; categoría válida"
    class EstadoTurno {
      <<enumeration>>
      PENDIENTE_ACEPTACION
      CONFIRMADO
      RECHAZADO
    }
    class Turno {
      -_id
      -_laboratorio_id
      -_asistente_id
      -_intervalo: IntervaloTiempo
      -_estado: EstadoTurno
      -_asignado_por
      +vigente: bool
      +confirmado: bool
      +aceptar()
      +rechazar()
    }
    note for Turno "inv: exactamente 1 asistente; empieza y termina el mismo día"
    class SolicitudDeAsignacion {
      <<value object>>
      +asistente: Asistente
      +laboratorio_id
      +intervalo
      +turnos_de_la_semana
      +turnos_del_laboratorio
      +ahora: datetime
    }
    class ReglaDeAsignacion {
      <<interface>>
      +verificar(solicitud)
    }
    class PoliticaDeAsignacion {
      -_reglas: tuple~ReglaDeAsignacion~
      +verificar(solicitud)
      +asignar(turno_id, asignado_por, solicitud) Turno
    }
    ReglaDeAsignacion <|.. TurnoDebeSerFuturo
    ReglaDeAsignacion <|.. AsistenteDebeEstarActivo
    ReglaDeAsignacion <|.. SinTraslapes
    ReglaDeAsignacion <|.. UnResponsablePorLaboratorio
    ReglaDeAsignacion <|.. DentroDelTopeSemanal
    PoliticaDeAsignacion o--> "1..*" ReglaDeAsignacion
    PoliticaDeAsignacion ..> Turno : crea
    PoliticaDeAsignacion ..> SolicitudDeAsignacion
    Asistente *-- Disponibilidad
    Disponibilidad *-- "0..*" BloqueDisponible
    Asistente --> Categoria
    Asistente --> EstadoAsistente
    Turno --> EstadoTurno
    Turno ..> IntervaloTiempo
```

## 8.4 Dominio: reservas

```mermaid
classDiagram
    class Laboratorio {
      -_id
      -_nombre
      -_campus
    }
    class Maquina {
      -_id
      -_laboratorio_id
      -_codigo
      -_estado: EstadoMaquina
      +en_servicio: bool
      +marcar_fuera_de_servicio()
      +marcar_reparada()
    }
    class EstadoReserva {
      <<enumeration>>
      ACTIVA
      EN_USO
      LIBERADA
      CANCELADA
    }
    class Reserva {
      -_id
      -_estudiante_id
      -_maquina_id
      -_intervalo: IntervaloTiempo
      -_estado: EstadoReserva
      +limite_de_llegada: datetime
      +ocupa_la_maquina: bool
      +cuenta_para_el_limite_semanal: bool
      +esta_activa_en(ahora) bool
      +registrar_llegada(ahora)
      +liberar_por_ausencia(ahora) bool
      +cancelar()
    }
    note for Reserva "inv: duración <= 2 h; mismo día"
    class ReglaDeReserva {
      <<interface>>
      +verificar(solicitud)
    }
    class PoliticaDeReserva {
      -_reglas
      +verificar(solicitud)
    }
    class SolicitudDeReserva {
      <<value object>>
      +reserva
      +maquina
      +ahora
      +turnos_del_laboratorio
      +reservas_de_la_maquina
      +reservas_activas_del_estudiante
      +reservas_de_la_semana
    }
    ReglaDeReserva <|.. MaquinaEnServicio
    ReglaDeReserva <|.. ReservaFutura
    ReglaDeReserva <|.. LaboratorioAbierto
    ReglaDeReserva <|.. MaquinaLibre
    ReglaDeReserva <|.. UnaReservaActivaALaVez
    ReglaDeReserva <|.. SeisHorasPorSemana
    PoliticaDeReserva o--> "1..*" ReglaDeReserva
    Laboratorio "1" o-- "*" Maquina
    Maquina "1" <-- "*" Reserva
    Reserva --> EstadoReserva
    SolicitudDeReserva --> Reserva
    SolicitudDeReserva --> Maquina
```

## 8.5 Dominio: pagos

```mermaid
classDiagram
    class Tarifario {
      -_id
      -_desde: date
      -_hasta: date?
      -_tarifas: dict~Categoria, Dinero~
      -_porcentaje_recargo: Decimal
      +factor_de_recargo: Decimal
      +tarifa_de(categoria) Dinero
      +aplica_en(fecha) bool
    }
    note for Tarifario "inv: tarifa > 0 para A y B; recargo >= 0; hasta >= desde"
    class CatalogoDeTarifas {
      -_tarifarios
      +vigente_en(fecha) Tarifario
    }
    note for CatalogoDeTarifas "inv: vigencias no traslapadas"
    class Asistencia {
      -_id
      -_turno_id
      -_asistente_id
      -_inicio_programado: datetime
      -_trabajado: IntervaloTiempo
      +minutos_trabajados: int
    }
    class PoliticaDeRecargo {
      <<interface>>
      +aplica(asistencia) bool
    }
    class RecargoNocturnoOFinDeSemana {
      +hora_nocturna: time = 18:00
      +aplica(asistencia) bool
    }
    class LiquidadorMensual {
      -_recargo: PoliticaDeRecargo
      +liquidar(mes, asistente, asistencias, tarifas) LiquidacionAsistente
    }
    class LiquidacionAsistente {
      <<value object>>
      +asistente_id
      +nombre
      +categoria
      +minutos_base
      +minutos_con_recargo
      +minutos_no_pagados
      +monto: Dinero
    }
    class CierreMensual {
      -_mes: Mes
      -_cerrado_en: datetime
      -_liquidaciones: tuple
      +total: Dinero
      +con_horas_no_pagadas
    }
    note for CierreMensual "inv: mes terminado; 1 liquidación por asistente; inmutable"
    PoliticaDeRecargo <|.. RecargoNocturnoOFinDeSemana
    LiquidadorMensual --> PoliticaDeRecargo
    LiquidadorMensual ..> CatalogoDeTarifas
    LiquidadorMensual ..> Asistencia
    LiquidadorMensual ..> LiquidacionAsistente : crea
    CatalogoDeTarifas o-- "*" Tarifario
    CierreMensual *-- "*" LiquidacionAsistente
```

## 8.6 Aplicación

```mermaid
classDiagram
    class AsignarTurno {
      +ejecutar(AsignarTurnoComando) TurnoAsignado
    }
    class ResponderTurnoPendiente {
      +ejecutar(ResponderTurnoComando) EstadoTurno
    }
    class ReservarMaquina {
      +ejecutar(ReservarMaquinaComando) ReservaRegistrada
    }
    class LiberarReservasNoPresentadas {
      +ejecutar() int
    }
    class CerrarMes {
      +ejecutar(CerrarMesComando) MesCerrado
    }
    class UnidadDeTrabajo {
      <<interface>>
      +turnos
      +reservas
      +asistentes
      +...
      +confirmar()
    }
    class Reloj {
      <<interface>>
      +ahora() datetime
    }
    class Notificador {
      <<interface>>
      +notificar(destinatario, asunto, mensaje)
    }
    class ExportadorPlanilla {
      <<interface>>
      +exportar(cierre) str
    }
    class DirectorioInstitucional {
      <<interface>>
      +buscar(id) Usuario?
    }
    AsignarTurno --> UnidadDeTrabajo
    AsignarTurno --> Reloj
    AsignarTurno --> Notificador
    AsignarTurno --> DirectorioInstitucional
    AsignarTurno --> PoliticaDeAsignacion
    ReservarMaquina --> PoliticaDeReserva
    CerrarMes --> ExportadorPlanilla
    CerrarMes --> LiquidadorMensual
    UnidadDeTrabajo <|.. UnidadDeTrabajoPostgres
    UnidadDeTrabajo <|.. UnidadDeTrabajoEnMemoria
    ExportadorPlanilla <|.. ExportadorCsvBecas
    Reloj <|.. RelojDelSistema
```

Los **comandos** (`AsignarTurnoComando`…) y los **resultados** (`TurnoAsignado`…) son
dataclasses inmutables: son los datos que cruzan la frontera del caso de uso.

## 8.7 Tabla de invariantes

| Clase | Invariante | Error | Prueba |
|-------|------------|-------|--------|
| `IntervaloTiempo` | fin > inicio; sin zona horaria | `E-INTERVALO-INVALIDO`, `E-DATO-INVALIDO` | `tests/dominio/test_comun.py::TestIntervaloTiempo` |
| `Dinero` | Decimal y >= 0 | `E-DATO-INVALIDO` | `TestDinero` |
| `Mes`, `SemanaISO` | Existen en el calendario | `E-DATO-INVALIDO` | `TestSemanaYMes` |
| `Usuario` | Un coordinador de laboratorio tiene exactamente 1 laboratorio | `E-DATO-INVALIDO` | `TestUsuario` |
| `Asistente` | 0 < tope ≤ 168, Decimal, categoría A o B | `E-DATO-INVALIDO` | `tests/dominio/test_horario.py::TestAsistente` |
| `Turno` | Exactamente un asistente; mismo día; transiciones solo desde PENDIENTE | `E-DATO-INVALIDO`, `E-TRANSICION-INVALIDA` | `TestTurno` |
| `Reserva` | ≤ 2 h; mismo día; llegada dentro de los 15 min | `E-RESERVA-MUY-LARGA`, `E-TRANSICION-INVALIDA` | `tests/dominio/test_reservas.py` |
| `Tarifario` | Tarifa > 0 para A y B; recargo ≥ 0; vigencia coherente | `E-DATO-INVALIDO` | `tests/dominio/test_pagos.py::TestTarifario` |
| `CatalogoDeTarifas` | Vigencias sin traslape | `E-DATO-INVALIDO` | ídem |
| `LiquidacionAsistente` | Horas ≥ 0; sin horas pagadas no hay monto | `E-DATO-INVALIDO` | `TestLiquidacionYCierre` |
| `CierreMensual` | Mes terminado; 1 liquidación por asistente; sin métodos que lo modifiquen | `E-MES-NO-TERMINADO`, `E-DATO-INVALIDO` | ídem |
