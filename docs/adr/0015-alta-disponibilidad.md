# ADR-0015 · Alta disponibilidad y aislamiento de carga

- **Estado:** aceptada (diseño). El prototipo implementa lo básico.

## Contexto
"Debe de contar con alta disponibilidad, overhead como procesos de matrícula, finales
de semestre etc, no deben de afectar el funcionamiento." No hay presupuesto para una
nube externa.

## Decisión
1. **API sin estado.** Ningún dato vive en memoria del proceso entre peticiones:
   - las sesiones las da el directorio;
   - los archivos se regeneran (ADR-0012);
   - las tareas periódicas son idempotentes.
   Por eso se puede correr **2 o más réplicas**.
2. **Balanceador** nginx con *health check* a `/api/salud`, y una IP virtual (keepalived) entre dos nodos.
3. **PostgreSQL 14 con replicación en streaming** a un nodo de respaldo y promoción manual o con Patroni. Además, respaldos diarios con `pg_dump` o `pgBackRest`.
4. **Aislamiento:** contenedores y base de datos **propios** de CompuLab, con reservas de CPU y memoria, sin compartir el servidor de base de datos con matrícula. La única dependencia en línea es el directorio al iniciar sesión.
5. **En el prototipo:** `restart: unless-stopped`, `HEALTHCHECK` en la imagen y `depends_on: service_healthy`.

## Alternativas consideradas
- Kubernetes con autoescalado. Es potente, pero no se sabe si la infraestructura del TEC lo ofrece, y el equipo no lo domina. Queda como evolución natural de las réplicas sin estado.
- Usar el servidor PostgreSQL institucional compartido. Va en contra del aislamiento de carga.

## Consecuencias
Se cumplen AC-02 y AC-03 sin servicios de pago. La conmutación de la base requiere un
procedimiento operativo (runbook) que debe documentar el equipo de infraestructura.
