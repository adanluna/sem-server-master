-- Crear tabla de videos
CREATE TABLE IF NOT EXISTS videos (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendiente',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de audios
CREATE TABLE IF NOT EXISTS audios (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendiente',
    video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de transcripciones
CREATE TABLE IF NOT EXISTS transcripciones (
    id SERIAL PRIMARY KEY,
    audio_id INTEGER REFERENCES audios(id) ON DELETE CASCADE,
    texto TEXT NOT NULL,
    formato TEXT DEFAULT 'plain',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
