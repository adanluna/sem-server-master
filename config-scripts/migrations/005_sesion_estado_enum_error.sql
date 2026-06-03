-- Añade 'error' al enum de estado de sesión (usado por registrar_error_procesamiento).
-- En algunos servidores el tipo se renombró a estado_sesion_enum_new durante migraciones previas.

DO $$
DECLARE
  t RECORD;
BEGIN
  FOR t IN
    SELECT typname
    FROM pg_type
    WHERE typname IN ('estado_sesion_enum', 'estado_sesion_enum_new')
  LOOP
    IF NOT EXISTS (
      SELECT 1
      FROM pg_enum e
      JOIN pg_type ty ON e.enumtypid = ty.oid
      WHERE ty.typname = t.typname
        AND e.enumlabel = 'error'
    ) THEN
      EXECUTE format(
        'ALTER TYPE %I ADD VALUE %L',
        t.typname,
        'error'
      );
    END IF;
  END LOOP;
END $$;
