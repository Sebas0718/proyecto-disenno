# ADR-0012 · Archivo para Becas en CSV, detrás de un puerto

- **Estado:** aceptada (el formato exacto hay que confirmarlo con Becas)

## Contexto
"Generando el archivo que Becas acepta". El enunciado no especifica el formato.

## Decisión
- Puerto `ExportadorPlanilla.exportar(cierre) -> ubicación`.
- Adaptador `ExportadorCsvBecas`. Formato:
  - UTF-8, separador coma, punto decimal;
  - una fila por asistente;
  - columnas `anio, mes, asistente_id, nombre, categoria, horas_base, horas_con_recargo, horas_no_pagadas, monto_colones`.
- El CSV se **regenera** desde el cierre guardado cuando se descarga. Como el cierre es inmutable, el archivo siempre es idéntico, y cualquier réplica lo puede servir sin compartir disco.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| Excel (.xlsx) | Agrega una biblioteca. El CSV se abre igual en cualquier hoja de cálculo. |
| JSON | Es menos amigable para una oficina. |
| Guardar el archivo y servirlo desde disco | Obliga a compartir almacenamiento entre réplicas (AC-02). |

## Consecuencias
Si Becas pide otro formato, se escribe otro adaptador y se cambia **una línea** en
`compulab/api/composicion.py`.
