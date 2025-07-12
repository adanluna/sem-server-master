-- docker exec -i postgres_db psql -U postgres -d semefo < /Users/adanluna/semefo/config-scripts/api.sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50), -- 'audio' o 'video'
    archivo_original VARCHAR(255),
    resultado VARCHAR(255),
    status VARCHAR(20), -- 'pendiente', 'procesando', 'completado', 'error'
    fecha_inicio TIMESTAMP DEFAULT NOW(),
    fecha_fin TIMESTAMP,
    error TEXT
);

CREATE TABLE videos (
    id SERIAL PRIMARY KEY,
    archivo VARCHAR(255),
    webm VARCHAR(255),
    creado TIMESTAMP DEFAULT NOW()
);

CREATE TABLE audios (
    id SERIAL PRIMARY KEY,
    archivo VARCHAR(255),
    creado TIMESTAMP DEFAULT NOW()
);

CREATE TABLE transcripciones (
    id SERIAL PRIMARY KEY,
    audio_id INT REFERENCES audios(id),
    texto TEXT,
    creado TIMESTAMP DEFAULT NOW()
);

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
    usuario_ldap VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS sesion_archivos (
    id SERIAL PRIMARY KEY,
    sesion_id INTEGER NOT NULL REFERENCES sesiones(id) ON DELETE CASCADE,
    tipo_archivo VARCHAR(50),
    ruta_original TEXT,
    ruta_convertida TEXT,
    conversion_completa BOOLEAN DEFAULT FALSE,
    transcripcion_completa BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS logs_eventos (
    id SERIAL PRIMARY KEY,
    tipo_evento VARCHAR(100),
    descripcion TEXT,
    usuario_ldap VARCHAR(255),
    fecha TIMESTAMP DEFAULT NOW()
);

ALTER TABLE sesiones ADD COLUMN IF NOT EXISTS tablet_id VARCHAR(255);
ALTER TABLE sesiones ADD COLUMN IF NOT EXISTS plancha_id VARCHAR(255);
ALTER TABLE sesiones ADD COLUMN IF NOT EXISTS estado VARCHAR(20) DEFAULT 'en_progreso';
ALTER TABLE sesiones ADD COLUMN IF NOT EXISTS user_nombre VARCHAR(255);

