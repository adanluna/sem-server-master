-- Tamaño en KB persistido al completar procesamiento (workers)
ALTER TABLE sesion_archivos
  ADD COLUMN IF NOT EXISTS tamano_kb DOUBLE PRECISION;
