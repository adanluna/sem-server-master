-- =====================================================================
--  SEMEFO - ESTRUCTURA EXTENDIDA OFICIAL (POSTGRESQL 15)
-- =====================================================================

\connect semefo;

-- ===============================================
-- ENUMS
-- ===============================================

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

-- ===============================================
-- TABLA: investigaciones
-- ===============================================

CREATE TABLE IF NOT EXISTS investigaciones (
    id SERIAL PRIMARY KEY,
    numero_expediente VARCHAR(100) UNIQUE NOT NULL,
    nombre_carpeta VARCHAR(255),
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    observaciones TEXT
);

-- ===============================================
-- TABLA: sesiones
-- ===============================================

CREATE TABLE IF NOT EXISTS sesiones (
    id SERIAL PRIMARY KEY,
    investigacion_id INTEGER NOT NULL REFERENCES investigaciones(id) ON DELETE CASCADE,
    nombre_sesion VARCHAR(255),
    fecha TIMESTAMP DEFAULT NOW(),
    observaciones TEXT,
    usuario_ldap VARCHAR(255) NOT NULL,
    tablet_id VARCHAR(255),
    plancha_id VARCHAR(255),
    camara VARCHAR(255),
    estado estado_sesion_enum DEFAULT 'en_progreso',
    user_nombre VARCHAR(255),
    fecha_cierre TIMESTAMP,
    ultima_actualizacion TIMESTAMP DEFAULT NOW()
);

-- ===============================================
-- TABLA: dispositivos (tablets / cámaras / planchas)
-- ===============================================

CREATE TABLE IF NOT EXISTS dispositivos (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL,   -- tablet, camara, plancha
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    fecha_registro TIMESTAMP DEFAULT NOW()
);

-- ===============================================
-- TABLA: jobs
-- ===============================================

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

-- ===============================================
-- TABLA: sesion_archivos
-- ===============================================

CREATE TABLE IF NOT EXISTS sesion_archivos (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER NOT NULL REFERENCES sesiones(id) ON DELETE CASCADE,
    tipo_archivo tipo_archivo_enum NOT NULL,
    ruta_original TEXT,
    ruta_convertida TEXT,
    conversion_completa BOOLEAN DEFAULT FALSE,
    estado estado_archivo_enum DEFAULT 'pendiente',
    mensaje TEXT,
    fecha_finalizacion TIMESTAMP,
    fecha TIMESTAMP DEFAULT NOW()
);

-- ===============================================
-- TABLA: transcripciones
-- ===============================================

CREATE TABLE IF NOT EXISTS transcripciones (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER REFERENCES sesiones(id) ON DELETE CASCADE,
    ruta_archivo TEXT NOT NULL,
    texto TEXT,
    fecha TIMESTAMP DEFAULT NOW()
);

-- ===============================================
-- TABLA: manifest
-- ===============================================

CREATE TABLE IF NOT EXISTS manifest (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER REFERENCES sesiones(id) ON DELETE CASCADE,
    carpeta_dia VARCHAR(255),
    total_archivos INTEGER,
    fecha TIMESTAMP DEFAULT NOW()
);

-- ===============================================
-- TABLA: logs_eventos
-- ===============================================

CREATE TABLE IF NOT EXISTS logs_eventos (
    id SERIAL PRIMARY KEY,
    tipo_evento VARCHAR(100),
    descripcion TEXT,
    usuario_ldap VARCHAR(255),
    fecha TIMESTAMP DEFAULT NOW()
);

-- ===============================================
-- TABLA: usuarios (admins internos del sistema)
-- ===============================================

CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    usuario_ldap VARCHAR(255) UNIQUE NOT NULL,
    nombre VARCHAR(255),
    rol VARCHAR(50),  -- admin, forense, sistema
    fecha TIMESTAMP DEFAULT NOW()
);

-- ===============================================
-- VISTA: estatus_archivos (para endpoint /estatus_archivos)
-- ===============================================

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

-- ===============================================
-- TRIGGER: actualizar fecha_actualizacion en jobs
-- ===============================================

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

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
