-- Persistir JSON de procesamiento y errores para reproceso desde dashboard
ALTER TABLE sesiones
  ADD COLUMN IF NOT EXISTS payload_procesamiento JSONB,
  ADD COLUMN IF NOT EXISTS error_procesamiento TEXT,
  ADD COLUMN IF NOT EXISTS error_origen VARCHAR(100),
  ADD COLUMN IF NOT EXISTS fecha_error_procesamiento TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS reintentos_procesamiento INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS fecha_ultimo_procesamiento TIMESTAMPTZ;
