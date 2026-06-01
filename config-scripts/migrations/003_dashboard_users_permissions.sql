-- Permisos por sección del panel (JSON). Reemplaza el uso operativo de roles CSV.
ALTER TABLE dashboard_users
    ADD COLUMN IF NOT EXISTS permissions JSONB NOT NULL DEFAULT '{}'::jsonb;

-- admin: todo habilitado
UPDATE dashboard_users
SET permissions = '{
  "dashboard": true,
  "sesiones": true,
  "sesiones_fallidas": true,
  "jobs": true,
  "planchas": true,
  "tokens": true,
  "infraestructura": true,
  "usuarios": true
}'::jsonb
WHERE username = 'admin';

-- dashboard_admin (no admin): todas las secciones excepto gestión de usuarios opcional — damos todas
UPDATE dashboard_users
SET permissions = '{
  "dashboard": true,
  "sesiones": true,
  "sesiones_fallidas": true,
  "jobs": true,
  "planchas": true,
  "tokens": true,
  "infraestructura": true,
  "usuarios": false
}'::jsonb
WHERE username <> 'admin'
  AND roles LIKE '%dashboard_admin%'
  AND (permissions IS NULL OR permissions = '{}'::jsonb);

-- dashboard_read: lectura básica
UPDATE dashboard_users
SET permissions = '{
  "dashboard": true,
  "sesiones": true,
  "sesiones_fallidas": false,
  "jobs": true,
  "planchas": true,
  "tokens": false,
  "infraestructura": false,
  "usuarios": false
}'::jsonb
WHERE username <> 'admin'
  AND roles NOT LIKE '%dashboard_admin%'
  AND (permissions IS NULL OR permissions = '{}'::jsonb);
