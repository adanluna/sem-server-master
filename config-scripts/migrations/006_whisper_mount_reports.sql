-- Reportes HTTP de montaje WAVE desde servidor Whisper (canal fiable sin depender del share CIFS)

CREATE TABLE IF NOT EXISTS whisper_mount_reports (
    id SERIAL PRIMARY KEY,
    host VARCHAR(100) NOT NULL DEFAULT 'whisper',
    mount_point VARCHAR(255) NOT NULL,
    probe_path VARCHAR(512),
    mounted BOOLEAN NOT NULL,
    readable BOOLEAN NOT NULL,
    ok BOOLEAN NOT NULL,
    message VARCHAR(512),
    reported_at TIMESTAMPTZ,
    fecha TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_whisper_mount_reports_fecha
    ON whisper_mount_reports (fecha DESC);
