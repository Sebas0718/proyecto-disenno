-- CompuLab · Esquema de la base de datos (PostgreSQL 14)
--
-- Las reglas del negocio viven en el dominio (Python). La base de datos repite
-- las más críticas como *defensa en profundidad* (ADR-0004): si dos
-- coordinadores asignan un turno al mismo tiempo, las dos transacciones pasan
-- la verificación en Python, pero la restricción EXCLUDE deja entrar solo a una.
--
-- Todas las horas son "timestamp without time zone" en hora local de Costa Rica
-- (ADR-0009).

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;

-- --------------------------------------------------------------------------
-- Laboratorios y máquinas
-- --------------------------------------------------------------------------
CREATE TABLE laboratorio (
    id      text PRIMARY KEY,
    nombre  text NOT NULL,
    campus  text NOT NULL
);

CREATE TABLE maquina (
    id              text PRIMARY KEY,
    laboratorio_id  text NOT NULL REFERENCES laboratorio (id),
    codigo          text NOT NULL,
    estado          text NOT NULL CHECK (estado IN ('EN_SERVICIO', 'FUERA_DE_SERVICIO')),
    UNIQUE (laboratorio_id, codigo)
);

-- --------------------------------------------------------------------------
-- Asistentes y su disponibilidad declarada
-- --------------------------------------------------------------------------
CREATE TABLE asistente (
    id                    text PRIMARY KEY,           -- id del directorio institucional
    nombre                text NOT NULL,
    categoria             text NOT NULL CHECK (categoria IN ('A', 'B')),
    tope_horas_semanales  numeric(5, 2) NOT NULL
                          CHECK (tope_horas_semanales > 0 AND tope_horas_semanales <= 168),
    estado                text NOT NULL CHECK (estado IN ('ACTIVO', 'RENUNCIO', 'DADO_DE_BAJA'))
);

CREATE TABLE bloque_disponible (
    asistente_id  text NOT NULL REFERENCES asistente (id) ON DELETE CASCADE,
    dia_semana    smallint NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),  -- 0 = lunes
    hora_inicio   time NOT NULL,
    hora_fin      time NOT NULL,
    CHECK (hora_fin > hora_inicio),
    PRIMARY KEY (asistente_id, dia_semana, hora_inicio)
);

-- --------------------------------------------------------------------------
-- Turnos
-- --------------------------------------------------------------------------
CREATE SEQUENCE turno_numero;

CREATE TABLE turno (
    id              text PRIMARY KEY,
    laboratorio_id  text NOT NULL REFERENCES laboratorio (id),
    asistente_id    text NOT NULL REFERENCES asistente (id),   -- exactamente un responsable
    asignado_por    text NOT NULL,
    inicio          timestamp NOT NULL,
    fin             timestamp NOT NULL,
    estado          text NOT NULL
                    CHECK (estado IN ('PENDIENTE_ACEPTACION', 'CONFIRMADO', 'RECHAZADO')),
    CHECK (fin > inicio),
    CHECK (inicio::date = fin::date),
    -- Regla 1 del enunciado: un asistente no tiene dos turnos que se traslapen,
    -- en ningún laboratorio ni campus.
    CONSTRAINT turno_sin_traslape_del_asistente
        EXCLUDE USING gist (asistente_id WITH =, tsrange(inicio, fin) WITH &&)
        WHERE (estado <> 'RECHAZADO'),
    -- "Exactamente una persona responsable": un laboratorio no tiene dos turnos a la vez.
    CONSTRAINT turno_un_responsable_por_laboratorio
        EXCLUDE USING gist (laboratorio_id WITH =, tsrange(inicio, fin) WITH &&)
        WHERE (estado <> 'RECHAZADO')
);

CREATE INDEX turno_por_asistente ON turno (asistente_id, inicio);

-- --------------------------------------------------------------------------
-- Reservas de máquinas
-- --------------------------------------------------------------------------
CREATE SEQUENCE reserva_numero;

CREATE TABLE reserva (
    id             text PRIMARY KEY,
    estudiante_id  text NOT NULL,                              -- id del directorio institucional
    maquina_id     text NOT NULL REFERENCES maquina (id),
    inicio         timestamp NOT NULL,
    fin            timestamp NOT NULL,
    estado         text NOT NULL CHECK (estado IN ('ACTIVA', 'EN_USO', 'LIBERADA', 'CANCELADA')),
    CHECK (fin > inicio),
    CHECK (fin - inicio <= interval '2 hours'),                 -- "no puede pasar de dos horas"
    -- Una máquina no se reserva dos veces en la misma franja.
    CONSTRAINT reserva_sin_traslape_en_maquina
        EXCLUDE USING gist (maquina_id WITH =, tsrange(inicio, fin) WITH &&)
        WHERE (estado IN ('ACTIVA', 'EN_USO'))
);

CREATE INDEX reserva_por_estudiante ON reserva (estudiante_id, inicio);
CREATE INDEX reserva_activas ON reserva (inicio) WHERE estado = 'ACTIVA';

-- --------------------------------------------------------------------------
-- Asistencias (marcas reales de entrada y salida)
-- --------------------------------------------------------------------------
CREATE TABLE asistencia (
    id                 text PRIMARY KEY,
    turno_id           text NOT NULL UNIQUE REFERENCES turno (id),
    asistente_id       text NOT NULL REFERENCES asistente (id),
    inicio_programado  timestamp NOT NULL,
    entrada            timestamp NOT NULL,
    salida             timestamp NOT NULL,
    CHECK (salida > entrada),
    CHECK (entrada::date = salida::date)
);

CREATE INDEX asistencia_por_entrada ON asistencia (entrada);

-- --------------------------------------------------------------------------
-- Tarifas (datos con vigencia, ADR-0006)
-- --------------------------------------------------------------------------
CREATE TABLE tarifario (
    id                  text PRIMARY KEY,
    vigente_desde       date NOT NULL,
    vigente_hasta       date,                                  -- NULL = sin fecha de fin
    porcentaje_recargo  numeric(5, 2) NOT NULL CHECK (porcentaje_recargo >= 0),
    CHECK (vigente_hasta IS NULL OR vigente_hasta >= vigente_desde),
    CONSTRAINT tarifario_sin_vigencias_traslapadas
        EXCLUDE USING gist (daterange(vigente_desde, vigente_hasta, '[]') WITH &&)
);

CREATE TABLE tarifa_categoria (
    tarifario_id    text NOT NULL REFERENCES tarifario (id) ON DELETE CASCADE,
    categoria       text NOT NULL CHECK (categoria IN ('A', 'B')),
    monto_por_hora  numeric(12, 2) NOT NULL CHECK (monto_por_hora > 0),
    PRIMARY KEY (tarifario_id, categoria)
);

-- --------------------------------------------------------------------------
-- Cierres mensuales (inmutables)
-- --------------------------------------------------------------------------
CREATE TABLE cierre_mensual (
    anio        smallint NOT NULL,
    mes         smallint NOT NULL CHECK (mes BETWEEN 1 AND 12),
    cerrado_en  timestamp NOT NULL,
    PRIMARY KEY (anio, mes)                    -- un mes se cierra una sola vez
);

CREATE TABLE liquidacion (
    anio                 smallint NOT NULL,
    mes                  smallint NOT NULL,
    asistente_id         text NOT NULL REFERENCES asistente (id),
    nombre               text NOT NULL,       -- copia: el cierre no cambia si cambia el nombre
    categoria            text NOT NULL CHECK (categoria IN ('A', 'B')),
    minutos_base         integer NOT NULL CHECK (minutos_base >= 0),
    minutos_con_recargo  integer NOT NULL CHECK (minutos_con_recargo >= 0),
    minutos_no_pagados   integer NOT NULL CHECK (minutos_no_pagados >= 0),
    monto                numeric(12, 2) NOT NULL CHECK (monto >= 0),
    PRIMARY KEY (anio, mes, asistente_id),
    FOREIGN KEY (anio, mes) REFERENCES cierre_mensual (anio, mes)
);

-- "Un mes cerrado no se vuelve a calcular ni se corrige."
CREATE FUNCTION impedir_modificar_mes_cerrado() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Un mes cerrado no se modifica (%).', TG_TABLE_NAME
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;

CREATE TRIGGER cierre_mensual_inmutable
    BEFORE UPDATE OR DELETE ON cierre_mensual
    FOR EACH ROW EXECUTE FUNCTION impedir_modificar_mes_cerrado();

CREATE TRIGGER liquidacion_inmutable
    BEFORE UPDATE OR DELETE ON liquidacion
    FOR EACH ROW EXECUTE FUNCTION impedir_modificar_mes_cerrado();
