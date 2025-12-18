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

ALTER TABLE sesiones
DROP COLUMN plancha_id;

ALTER TABLE sesiones
ADD COLUMN plancha_id INTEGER REFERENCES planchas(id),
ADD COLUMN plancha_nombre VARCHAR(255);