# ADR-0006 · Tarifas como datos con vigencia, y dinero con Decimal

- **Estado:** aceptada

## Contexto
"Las tarifas de cada categoría y el porcentaje del recargo los fija la Coordinación de
Soporte y [...] se los cambian casi cada semestre y casi nunca con tiempo."

## Decisión
1. `Tarifario` es una entidad con:
   - `vigente_desde` y `vigente_hasta`;
   - una tarifa por categoría;
   - el porcentaje de recargo.
2. `CatalogoDeTarifas` garantiza que las vigencias **no se traslapan**. También está garantizado en la base.
3. Al cerrar el mes, **cada asistencia** se paga con el tarifario vigente en su fecha. Así, un cambio a mitad de mes se aplica bien.
4. El dinero es el objeto de valor `Dinero(Decimal)`. Se rechaza `float` y se redondea a céntimos con `ROUND_HALF_UP` **solo al final**.

## Alternativas consideradas
| Alternativa | Por qué no |
|-------------|------------|
| Constantes en el código o en un archivo de configuración | Cada cambio requiere desplegar, y eso no cumple AC-04. |
| Un solo tarifario "actual" que se sobrescribe | Se pierde la historia y no se pueden pagar bien los meses en que cambió. |
| `float` para montos | `0.1 + 0.2 = 0.30000000000000004`: aparecen diferencias de céntimos con Becas. |

## Consecuencias
- **A favor:** cambiar tarifas no requiere código, y los cálculos son exactos.
- **En contra:** si falta un tarifario para alguna fecha, el cierre se detiene (`E-SIN-TARIFARIO`). Es intencional: es mejor no cerrar que pagar mal.
