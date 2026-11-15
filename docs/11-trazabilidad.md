# 11. Trazabilidad

La trazabilidad permite seguir cada requisito hasta el código que lo cumple y la prueba
que lo demuestra, y también recorrer el camino al revés.

## 11.1 Requerimiento → caso de uso → contrato → clases → pruebas

Pruebas: `A/` = `tests/aplicacion/`, `D/` = `tests/dominio/`, `I/` = `tests/integracion/`.

| RF | CU / contrato | Clases y métodos | Pruebas |
|----|---------------|------------------|---------|
| RF-07 Asignar turno | CU-07 · CO-01 PC1, PC2, PC5 | `AsignarTurno.ejecutar`, `PoliticaDeAsignacion.asignar`, `Turno` | `A/test_asignar_turno.py::test_pc1_*`, `test_pc2_*`, `test_pc5_*`; `I/test_postgres.py::test_caso_de_uso_asignar_turno_de_punta_a_punta` |
| RF-08 Sin traslapes | CU-07 ext. 7a | `SinTraslapes`, `IntervaloTiempo.se_traslapa_con`, restricción `turno_sin_traslape_del_asistente` | `test_ext_7a_*` (3); `D/test_comun.py::test_traslape`; `I/…::test_restriccion_de_traslape_aunque_se_salte_el_dominio` |
| RF-09 Tope semanal | CU-07 ext. 8a | `DentroDelTopeSemanal`, `Asistente.tope_minutos_semanales`, bloqueo `FOR UPDATE` | `test_ext_8a_*` (3); `D/test_horario.py::test_los_pendientes_tambien_cuentan_para_el_tope` |
| RF-10 Disponibilidad o aceptación | CU-07 PC3, PC4, ext. 9a; CU-08 | `Disponibilidad.incluye`, `Turno.aceptar/rechazar`, `ResponderTurnoPendiente` | `test_pc3_*`, `test_pc4_*`, `test_ext_9a_*`, `test_ext_9a1_*` a `test_ext_9a4_*` |
| RF-11 Asistente inactivo | CU-07 ext. 6c | `AsistenteDebeEstarActivo`, `Asistente.renunciar/dar_de_baja` | `test_ext_6c_*` (2 casos); `D/…::test_renunciar_y_dar_de_baja` |
| RF-12 Permisos de horario | CU-07 ext. 4b | `Usuario.puede_administrar_horario`, `Consultas.horario` | `test_ext_4b_*` (3); `tests/api/test_api.py::test_un_coordinador_de_laboratorio_no_ve_el_horario_de_otro` |
| "Exactamente una persona responsable" | CU-07 ext. 7b | `UnResponsablePorLaboratorio`, restricción `turno_un_responsable_por_laboratorio` | `test_ext_7b_*`; `I/…::test_restriccion_de_un_responsable_por_laboratorio` |
| RF-18 Reservar | CU-15 · CO-02 PC1 a PC5, ext. 4a a 10a | `ReservarMaquina`, `Reserva`, `PoliticaDeReserva` (6 reglas), `cubren` | `A/test_reservar_maquina.py::test_pc1_*` a `test_pc5_*`, `test_ext_4a_*` a `test_ext_10a_*`; `I/…::test_reservar_y_restriccion_de_maquina_ocupada` |
| RF-19 Liberar a los 15 min | CU-16 · CU-15 ext. 11a | `Reserva.liberar_por_ausencia`, `LiberarReservasNoPresentadas` | `test_ext_11a_*`; `D/test_reservas.py::test_liberar_por_ausencia_es_idempotente` |
| RF-23 Cerrar el mes | CU-19 · CO-03 PC1 a PC5 | `CerrarMes`, `LiquidadorMensual`, `RecargoNocturnoOFinDeSemana`, `CatalogoDeTarifas` | `A/test_cerrar_mes.py::test_pc1_*` a `test_pc5_*` (9 pruebas) |
| RF-24 Archivo Becas | CU-19 PC7 | `ExportadorPlanilla`, `ExportadorCsvBecas`, `contenido_csv` | `test_pc7_*`; `tests/api/test_api.py::test_cerrar_mes_y_descargar_el_csv` |
| RF-25 Mes inmutable | CU-19 PC6, ext. 3b | `CierreMensual` (sin métodos que lo modifiquen), PK `(anio, mes)`, trigger | `test_pc6_*`, `test_ext_3b_*`; `I/…::test_cerrar_mes_y_el_cierre_es_inmutable_en_la_base` |
| RF-26 Tarifas cambiantes | CU-20 (diseño), usado en CU-19 | `Tarifario`, `CatalogoDeTarifas.vigente_en` | `test_pc5_si_el_tarifario_cambia_a_mitad_de_mes_*`, `test_ext_5b_*`; `D/test_pagos.py::TestTarifario` |
| RF-27 Identificarse | CU-21 | `DirectorioInstitucional`, `identificar()` | `test_precondicion_solicitante_desconocido_en_el_directorio`; `test_sin_identificarse_responde_401` |
| RF-01 a RF-06, RF-13 a RF-17, RF-20 a RF-22 | CU-01 a CU-06, CU-09 a CU-14, CU-17, CU-18 | Diseñados (sección 2.6, diagramas de estado 9.5 a 9.7) | No implementados (fuera del mínimo exigido) |

## 11.2 Contratos → pruebas (verificación del requisito "una por poscondición y por extensión")

### CO-01 / CU-07 (`tests/aplicacion/test_asignar_turno.py`)
| Elemento | Prueba |
|----------|--------|
| PC1 | `test_pc1_se_crea_una_instancia_de_turno` |
| PC2 | `test_pc2_el_turno_queda_asociado_a_laboratorio_asistente_dia_horas_y_coordinador` |
| PC3 | `test_pc3_bloque_declarado_queda_confirmado` |
| PC4 | `test_pc4_bloque_no_declarado_queda_pendiente_y_se_avisa_al_asistente` |
| PC5 | `test_pc5_el_turno_queda_persistido_y_cuenta_para_las_siguientes_asignaciones` |
| 4a | `test_ext_4a_laboratorio_inexistente` |
| 4b | `test_ext_4b_coordinador_de_otro_laboratorio_no_puede_asignar`, `…_un_estudiante_no_puede_asignar`, `…_el_coordinador_de_soporte_puede_asignar_en_cualquier_laboratorio` |
| 5a | `test_ext_5a_hora_de_fin_no_posterior_al_inicio` |
| 6a | `test_ext_6a_asistente_inexistente` |
| 6b | `test_ext_6b_turno_en_el_pasado` |
| 6c | `test_ext_6c_asistente_inactivo[RENUNCIO]`, `[DADO_DE_BAJA]` |
| 7a | `test_ext_7a_traslape_aunque_sea_en_otro_laboratorio_y_campus`, `…_turnos_seguidos_no_se_traslapan`, `…_un_turno_rechazado_no_cuenta_como_traslape` |
| 7b | `test_ext_7b_el_laboratorio_ya_tiene_responsable_en_esa_franja` |
| 8a | `test_ext_8a_supera_el_tope_semanal_sumando_todos_los_laboratorios`, `…_llegar_exactamente_al_tope_si_se_permite`, `…_los_turnos_de_otra_semana_no_cuentan` |
| 9a | `test_ext_9a_fuera_de_disponibilidad_queda_pendiente` |
| 9a1 | `test_ext_9a1_el_asistente_acepta_y_queda_confirmado` |
| 9a2 | `test_ext_9a2_el_asistente_rechaza_y_se_avisa_al_coordinador` |
| 9a3 | `test_ext_9a3_solo_el_asistente_del_turno_puede_responder` |
| 9a4 | `test_ext_9a4_no_se_responde_un_turno_que_no_esta_pendiente` |

### CO-02 / CU-15 (`tests/aplicacion/test_reservar_maquina.py`)
| Elemento | Prueba |
|----------|--------|
| PC1 | `test_pc1_se_crea_una_instancia_de_reserva` |
| PC2 | `test_pc2_la_reserva_queda_asociada_al_estudiante_maquina_y_franja` |
| PC3 | `test_pc3_la_reserva_queda_activa` |
| PC4 | `test_pc4_el_limite_de_llegada_es_el_inicio_mas_15_minutos` |
| PC5 | `test_pc5_la_reserva_queda_persistida_y_ocupa_la_maquina` |
| 4a | `test_ext_4a_solo_los_estudiantes_reservan` |
| 5a | `test_ext_5a_maquina_inexistente` |
| 5b | `test_ext_5b_maquina_fuera_de_servicio` |
| 6a | `test_ext_6a_fin_no_posterior_al_inicio` |
| 6b | `test_ext_6b_mas_de_dos_horas` |
| 6c | `test_ext_6c_franja_en_el_pasado` |
| 7a | `test_ext_7a_laboratorio_cerrado_sin_turno`, `…_en_parte_de_la_franja`, `…_un_turno_pendiente_no_abre_el_laboratorio` |
| 8a | `test_ext_8a_maquina_ocupada_en_esa_franja`, `…_otra_maquina_del_mismo_laboratorio_si_esta_libre` |
| 9a | `test_ext_9a_ya_tiene_una_reserva_activa` |
| 10a | `test_ext_10a_mas_de_seis_horas_en_la_semana`, `…_las_canceladas_no_cuentan_para_el_limite` |
| 11a | `test_ext_11a_si_no_se_presenta_en_15_minutos_se_libera_y_la_maquina_queda_libre` |

### CO-03 / CU-19 (`tests/aplicacion/test_cerrar_mes.py`)
| Elemento | Prueba |
|----------|--------|
| PC1 | `test_pc1_se_crea_el_cierre_del_mes_con_la_fecha_de_cierre` |
| PC2 | `test_pc2_una_liquidacion_por_asistente_que_trabajo_en_el_mes` |
| PC3 | `test_pc3_las_horas_de_turnos_nocturnos_o_de_fin_de_semana_llevan_recargo`, `…_se_aplica_una_sola_vez_si_es_sabado_en_la_noche`, `…_depende_del_inicio_programado_no_de_la_llegada` |
| PC4 | `test_pc4_las_horas_sobre_el_tope_semanal_quedan_sin_pagar_y_son_las_ultimas`, `…_las_horas_del_mes_anterior_en_la_misma_semana_cuentan_para_el_tope` |
| PC5 | `test_pc5_el_monto_usa_la_tarifa_de_la_categoria_y_redondea_a_centimos`, `…_si_el_tarifario_cambia_a_mitad_de_mes_cada_hora_usa_el_vigente` |
| PC6 | `test_pc6_el_cierre_queda_registrado_y_el_mes_cerrado` |
| PC7 | `test_pc7_se_genera_el_archivo_para_becas_con_una_fila_por_liquidacion` |
| 2a | `test_ext_2a_solo_el_coordinador_de_soporte_cierra_el_mes[CL1]`, `[E1]` |
| 3a | `test_ext_3a_el_mes_todavia_no_termino` |
| 3b | `test_ext_3b_un_mes_cerrado_no_se_vuelve_a_calcular` |
| 4a | `test_ext_4a_sin_asistencias_el_cierre_queda_vacio` |
| 5a | `test_ext_5a_horas_no_pagadas_se_avisan_al_coordinador_de_soporte`, `…_sin_horas_no_pagadas_no_hay_aviso` |
| 5b | `test_ext_5b_sin_tarifario_vigente_no_se_cierra` |
| 7a | `test_ext_7a_si_falla_el_archivo_el_mes_no_queda_cerrado` |

## 11.3 Atributos de calidad → tácticas → evidencia

| AC | Táctica | Evidencia |
|----|---------|-----------|
| AC-01 Rendimiento | Índices; reglas sobre una semana; API sin estado | `001_esquema.sql` (índices); `Consultas` y casos de uso leen solo por periodo |
| AC-02 Disponibilidad | Réplicas sin estado, *health check*, reinicio automático, PostgreSQL replicado | `Dockerfile` (HEALTHCHECK), `docker-compose.yml` (restart, healthcheck), ADR-0015 |
| AC-03 Aislamiento | Despliegue propio; sin dependencias en línea | ADR-0015; puertos `DirectorioInstitucional` y `ExportadorPlanilla` |
| AC-04 Modificabilidad | Tarifas como datos; Strategy de recargo; puerto de exportación | `Tarifario`, `PoliticaDeRecargo`; prueba `test_pc5_si_el_tarifario_cambia_*` |
| AC-05 Integridad | Restricciones EXCLUDE, `FOR UPDATE`, unidad de trabajo | `tests/integracion/test_postgres.py` |
| AC-06 Usabilidad móvil | Mobile-first, botones de 44 px, una columna | `web/css/estilos.css`; [14-ux-ui.md](14-ux-ui.md) |
| AC-07 Seguridad | Permisos en el dominio verificados en el servidor | `Usuario.puede_*`; pruebas `test_ext_4b_*`, `test_ext_2a_*`, `tests/api/test_api.py` |
| AC-08 Testabilidad | Hexagonal, dobles, FF-1, FF-2 | `uv run pytest` → 153 pruebas en ~1,5 s (más 7 de integración con `-m integracion`); `tests/aptitud/` |

## 11.4 Interpretaciones → ADR → prueba

| Interpretación | ADR | Prueba que la fija |
|----------------|-----|--------------------|
| I-2 Semana partida | 0007 | `test_pc4_las_horas_del_mes_anterior_en_la_misma_semana_cuentan_para_el_tope` |
| I-3 Recargo una vez | 0008 | `test_pc3_el_recargo_se_aplica_una_sola_vez_si_es_sabado_en_la_noche` |
| I-4 Recargo por inicio programado | 0008 | `test_pc3_el_recargo_depende_del_inicio_programado_no_de_la_llegada` |
| I-5 Últimas horas sin pagar | 0008 | `test_pc4_las_horas_sobre_el_tope_semanal_quedan_sin_pagar_y_son_las_ultimas` |
| I-6 Turno pendiente | 0008 | `test_pc4_bloque_no_declarado_queda_pendiente_y_se_avisa_al_asistente` |
| I-7 Un responsable por laboratorio | 0008 | `test_ext_7b_el_laboratorio_ya_tiene_responsable_en_esa_franja` |
| I-8 Reserva activa | 0010 | `test_ext_9a_ya_tiene_una_reserva_activa` |
| I-9 Canceladas no cuentan, liberadas sí | 0010 | `test_ext_10a_*` (2) |
| I-12 Solo un turno confirmado abre el laboratorio | 0010 | `test_ext_7a_un_turno_pendiente_no_abre_el_laboratorio` |
