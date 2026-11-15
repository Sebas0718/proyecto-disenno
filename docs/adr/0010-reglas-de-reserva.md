# ADR-0010 · Qué es una reserva "activa" y qué cuenta para las 6 horas

- **Estado:** aceptada

## Contexto
"Un estudiante no puede tener más de una reserva activa a la vez ni acumular más de
seis horas reservadas en una misma semana." El enunciado no define "activa" ni dice
si las reservas canceladas o liberadas cuentan.

## Decisión
- **Activa:**
  - su estado es ACTIVA o EN_USO;
  - todavía no terminó (`fin > ahora`).

  Por eso, un estudiante con una reserva para mañana no puede hacer otra para pasado mañana hasta que la de mañana termine.
- **Cuenta para las 6 h:** todas las reservas de la semana ISO, **menos las CANCELADAS**. Las **LIBERADAS** por no presentarse **sí** cuentan, para desincentivar el ausentismo.
- **Laboratorio abierto:** solo los turnos **CONFIRMADOS** abren el laboratorio. Varios turnos seguidos pueden cubrir una reserva (función `cubren`).

## Alternativas consideradas
- Que "activa" signifique solo "en curso ahora". Permitiría acaparar varias reservas futuras, que es justo lo que se quiere evitar.
- Que las liberadas no cuenten. Así, no presentarse no tendría ningún costo.

## Consecuencias
Son reglas estrictas, pero justas. Cambiarlas toca un solo método de `Reserva`
(`esta_activa_en` o `cuenta_para_el_limite_semanal`).
