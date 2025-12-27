-- =====================================================================
--  SEMEFO - ESTRUCTURA OFICIAL UNIFICADA (POSTGRESQL 15)
-- =====================================================================

\connect semefo;

-- =====================================================
-- ENUMS
-- =====================================================

CREATE TYPE tipo_archivo_enum AS ENUM (
    'audio',
    'audio2',
    'video',
    'video2',
    'transcripcion'
);

CREATE TYPE estado_archivo_enum AS ENUM (
    'pendiente',
    'procesando',
    'completado',
    'error'
);

CREATE TYPE estado_sesion_enum AS ENUM (
    'en_progreso',
    'pausada',
    'finalizada'
);

CREATE TYPE estado_job_enum AS ENUM (
    'pendiente',
    'procesando',
    'completado',
    'error'
);

-- =====================================================
-- TABLA: investigaciones
-- =====================================================

CREATE TABLE IF NOT EXISTS investigaciones (
    id SERIAL PRIMARY KEY,
    numero_expediente VARCHAR(100) UNIQUE NOT NULL,
    nombre_carpeta VARCHAR(255),
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    observaciones TEXT
);

-- =====================================================
-- TABLA: planchas
-- =====================================================

CREATE TABLE IF NOT EXISTS planchas (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,

    camara1_ip INET,
    camara1_id VARCHAR(100),
    camara1_activa BOOLEAN DEFAULT TRUE,

    camara2_ip INET,
    camara2_id VARCHAR(100),
    camara2_activa BOOLEAN DEFAULT TRUE,

    fecha_registro TIMESTAMP DEFAULT NOW(),
    activo BOOLEAN DEFAULT TRUE,
    asignada BOOLEAN DEFAULT FALSE
);

-- =====================================================
-- TABLA: sesiones
-- =====================================================

CREATE TABLE IF NOT EXISTS sesiones (
    id SERIAL PRIMARY KEY,
    investigacion_id INTEGER NOT NULL REFERENCES investigaciones(id) ON DELETE CASCADE,

    nombre_sesion VARCHAR(255),
    usuario_ldap VARCHAR(255) NOT NULL,
    user_nombre VARCHAR(255),

    tablet_id VARCHAR(255),
    plancha_id INTEGER REFERENCES planchas(id),
    plancha_nombre VARCHAR(255),

    estado estado_sesion_enum DEFAULT 'en_progreso',

    inicio TIMESTAMP,
    fin TIMESTAMP,
    fecha_cierre TIMESTAMP,

    progreso_porcentaje DOUBLE PRECISION DEFAULT 0,
    pausas_detectadas JSONB DEFAULT '[]',

    camara1_mac_address VARCHAR(100),
    camara2_mac_address VARCHAR(100),
    app_version VARCHAR(50),

    observaciones TEXT,
    fecha TIMESTAMP DEFAULT NOW(),
    ultima_actualizacion TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TABLA: jobs
-- =====================================================

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    investigacion_id INTEGER REFERENCES investigaciones(id) ON DELETE CASCADE,
    sesion_id INTEGER REFERENCES sesiones(id) ON DELETE CASCADE,

    tipo tipo_archivo_enum NOT NULL,
    archivo VARCHAR(255),

    estado estado_job_enum DEFAULT 'pendiente',
    resultado VARCHAR(255),
    error TEXT,

    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TABLA: sesion_archivos
-- =====================================================

CREATE TABLE IF NOT EXISTS sesion_archivos (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER NOT NULL REFERENCES sesiones(id) ON DELETE CASCADE,

    tipo_archivo tipo_archivo_enum NOT NULL,

    ruta_original TEXT,
    ruta_convertida TEXT,

    sha256 TEXT,
    duracion_archivo_seg DOUBLE PRECISION,
    duracion_sesion_seg DOUBLE PRECISION,

    progreso_porcentaje DOUBLE PRECISION DEFAULT 0,

    conversion_completa BOOLEAN DEFAULT FALSE,
    estado estado_archivo_enum DEFAULT 'pendiente',
    mensaje TEXT,

    fecha_finalizacion TIMESTAMP,
    fecha TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TABLA: transcripciones
-- =====================================================

CREATE TABLE IF NOT EXISTS transcripciones (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER REFERENCES sesiones(id) ON DELETE CASCADE,
    ruta_archivo TEXT NOT NULL,
    texto TEXT,
    fecha TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TABLA: manifest
-- =====================================================

CREATE TABLE IF NOT EXISTS manifest (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER REFERENCES sesiones(id) ON DELETE CASCADE,
    carpeta_dia VARCHAR(255),
    total_archivos INTEGER,
    fecha TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TABLA: log_pausas
-- =====================================================

CREATE TABLE IF NOT EXISTS log_pausas (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER NOT NULL REFERENCES sesiones(id) ON DELETE CASCADE,
    inicio TIMESTAMP NOT NULL,
    fin TIMESTAMP NOT NULL,
    duracion DOUBLE PRECISION NOT NULL,
    fuente VARCHAR(20) NOT NULL
);

-- =====================================================
-- TABLA: logs_eventos
-- =====================================================

CREATE TABLE IF NOT EXISTS logs_eventos (
    id SERIAL PRIMARY KEY,
    tipo_evento VARCHAR(100),
    descripcion TEXT,
    usuario_ldap VARCHAR(255),
    fecha TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TABLA: usuarios
-- =====================================================

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    usuario_ldap VARCHAR(255) UNIQUE NOT NULL,
    nombre VARCHAR(255),
    rol VARCHAR(50),
    fecha TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- VISTA: estatus archivos
-- =====================================================

CREATE OR REPLACE VIEW vw_estatus_archivos AS
SELECT
    s.id AS sesion_id,
    s.nombre_sesion,
    sa.tipo_archivo,
    sa.estado,
    sa.ruta_convertida,
    sa.fecha_finalizacion
FROM sesiones s
LEFT JOIN sesion_archivos sa ON sa.sesion_id = s.id;

-- =====================================================
-- TRIGGER: actualizar fecha_actualizacion en jobs
-- =====================================================

CREATE OR REPLACE FUNCTION actualizar_fecha_actualizacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_actualizar_job ON jobs;

CREATE TRIGGER trigger_actualizar_job
BEFORE UPDATE ON jobs
FOR EACH ROW
EXECUTE FUNCTION actualizar_fecha_actualizacion();

-- ============================================================
-- AUTH: Dashboard Users (local)
-- ============================================================
CREATE TABLE IF NOT EXISTS dashboard_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    roles VARCHAR(255) NOT NULL DEFAULT 'dashboard_read',
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ NULL,

    last_login_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_dashboard_users_username ON dashboard_users (username);


-- ============================================================
-- AUTH: Service Clients (workers / integraciones)
-- ============================================================
CREATE TABLE IF NOT EXISTS service_clients (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(120) UNIQUE NOT NULL,
    client_secret_hash VARCHAR(255) NOT NULL,
    roles VARCHAR(255) NOT NULL DEFAULT 'worker',
    activo BOOLEAN NOT NULL DEFAULT TRUE,

    allowed_ips TEXT NULL,

    last_used_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_service_clients_client_id ON service_clients (client_id);


-- ============================================================
-- AUTH: Refresh Tokens (hash)
-- ============================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    subject VARCHAR(200) NOT NULL,
    jti VARCHAR(120) UNIQUE NOT NULL,
    token_hash VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ NULL,

    rotated_to_id INTEGER NULL REFERENCES refresh_tokens(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_refresh_tokens_subject ON refresh_tokens (subject);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_expires_at ON refresh_tokens (expires_at);


-- =====================================================
-- FIN
-- =====================================================

