-- Conectarse a la base
\connect semefo

-- Crear tablas necesarias
CREATE TABLE IF NOT EXISTS investigaciones (
    id SERIAL PRIMARY KEY,
    numero_expediente VARCHAR(100) UNIQUE NOT NULL,
    nombre_carpeta VARCHAR(255),
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    observaciones TEXT
);

CREATE TABLE IF NOT EXISTS sesiones (
    id SERIAL PRIMARY KEY,
    investigacion_id INTEGER NOT NULL REFERENCES investigaciones(id) ON DELETE CASCADE,
    nombre_sesion VARCHAR(255),
    fecha TIMESTAMP DEFAULT NOW(),
    observaciones TEXT,
    usuario_ldap VARCHAR(255) NOT NULL,
    tablet_id VARCHAR(255),
    plancha_id VARCHAR(255),
    estado VARCHAR(20) DEFAULT 'en_progreso',
    user_nombre VARCHAR(255),
    fecha_cierre TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    investigacion_id INTEGER REFERENCES investigaciones(id) ON DELETE CASCADE,
    sesion_id INTEGER REFERENCES sesiones(id) ON DELETE CASCADE,
    tipo VARCHAR(50), -- 'audio', 'video', 'transcripcion'
    archivo VARCHAR(255),
    estado VARCHAR(20), -- 'pendiente', 'procesando', 'completado', 'error'
    resultado VARCHAR(255),
    error TEXT,
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP DEFAULT NOW()
);

-- ✅ Tabla centralizada de archivos (audio, video, transcripción)
CREATE TABLE IF NOT EXISTS sesion_archivos (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER NOT NULL REFERENCES sesiones(id) ON DELETE CASCADE,
    tipo_archivo VARCHAR(50) NOT NULL,  -- audio, video, audio2, video2, transcripcion
    ruta_original TEXT,
    ruta_convertida TEXT,
    conversion_completa BOOLEAN DEFAULT FALSE,
    estado VARCHAR(50) DEFAULT 'pendiente',
    mensaje TEXT,
    fecha_finalizacion TIMESTAMP,
    fecha TIMESTAMP DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS logs_eventos (
    id SERIAL PRIMARY KEY,
    tipo_evento VARCHAR(100),
    descripcion TEXT,
    usuario_ldap VARCHAR(255),
    fecha TIMESTAMP DEFAULT NOW()
);
