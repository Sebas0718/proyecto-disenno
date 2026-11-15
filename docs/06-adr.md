# 6. Decisiones de arquitectura (ADR)

Un **ADR** (*Architecture Decision Record*) registra una decisión importante:

- **Contexto:** el problema que se quería resolver.
- **Decisión:** lo que se eligió.
- **Alternativas:** lo que se descartó y por qué.
- **Consecuencias:** lo que se gana y lo que se sacrifica.

Sirven para que cualquier integrante del equipo pueda defender cada decisión, y para
que alguien que llegue después entienda *por qué* el sistema es como es.

| ADR | Decisión | Atributo o requisito que responde |
|-----|----------|-----------------------------------|
| [0001](adr/0001-monolito-modular-hexagonal.md) | Monolito modular con arquitectura hexagonal | Regla de dependencia, testabilidad (AC-08) |
| [0002](adr/0002-python-fastapi-contenedores.md) | Python 3.12 + FastAPI en contenedores Linux | R-01, R-04 |
| [0003](adr/0003-postgresql-sql-plano.md) | PostgreSQL 14 con SQL plano, sin ORM | R-02, dominio independiente |
| [0004](adr/0004-restricciones-en-bd.md) | Reglas críticas también como restricciones de la base | Integridad (AC-05) |
| [0005](adr/0005-unidad-de-trabajo-y-bloqueo.md) | Unidad de trabajo y bloqueo pesimista del asistente | Integridad (AC-05) |
| [0006](adr/0006-tarifas-como-datos-y-decimal.md) | Tarifas como datos con vigencia; Decimal para el dinero | Modificabilidad (AC-04) |
| [0007](adr/0007-semana-iso-y-semanas-partidas.md) | Semana ISO y semanas partidas entre meses | Interpretación I-1, I-2, I-13 |
| [0008](adr/0008-interpretaciones-de-reglas.md) | Recargo una vez, horas no pagadas cronológicas, turno pendiente, un responsable por laboratorio | Interpretaciones I-3 a I-7 |
| [0009](adr/0009-hora-local.md) | Hora local de Costa Rica sin zona horaria | Interpretación I-11 |
| [0010](adr/0010-reglas-de-reserva.md) | Reserva "activa" y qué cuenta para las 6 h | Interpretaciones I-8, I-9, I-12 |
| [0011](adr/0011-directorio-simulado.md) | Directorio institucional detrás de un puerto (simulado) | RF-27, AC-07 |
| [0012](adr/0012-archivo-becas-csv.md) | Archivo para Becas en CSV detrás de un puerto | RF-24, I-10 |
| [0013](adr/0013-front-end-sin-framework.md) | Pantallas en HTML/CSS/JS sin framework | Entregable B (pantallas) |
| [0014](adr/0014-funciones-de-aptitud.md) | Funciones de aptitud FF-1 (import-linter) y FF-2 (AST) | Entregable B (funciones de aptitud) |
| [0015](adr/0015-alta-disponibilidad.md) | Réplicas sin estado, PostgreSQL replicado y despliegue aislado | Disponibilidad (AC-02), aislamiento (AC-03) |
| [0016](adr/0016-datos-de-demostracion.md) | Datos de demostración relativos a hoy | Demo reproducible |
