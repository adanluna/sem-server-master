Despliegue
1. Aplicar migración en PostgreSQL:

psql -U $DB_USER -d $DB_NAME -f config-scripts/migrations/001_sesiones_payload_procesamiento.sql
2. Reiniciar servicios:

docker compose restart fastapi celery_uniones celery_manifest dashboard
3. Rebuild del dashboard (si usas imagen Docker):

docker compose build dashboard && docker compose up -d dashboard
Notas
Sesiones que fallaron antes de este cambio no tendrán JSON guardado y no aparecerán para reprocesar hasta que se envíen de nuevo desde la app.
El listado solo incluye sesiones con payload_procesamiento guardado y que no estén finalizada.
Al reprocesar se incrementa reintentos_procesamiento y se resetean jobs/archivos en error.
-----
# 1. Migración
psql -U $DB_USER -d $DB_NAME -f config-scripts/migrations/002_sesion_archivos_tamano_kb.sql

# 2. Reiniciar servicios
docker compose restart fastapi celery_uniones
# En servidor Whisper:
sudo systemctl restart whisper-listener
----

## CRUD usuarios dashboard + permisos por sección

```bash
psql -U $DB_USER -d $DB_NAME -f config-scripts/migrations/003_dashboard_users_permissions.sql
docker compose restart fastapi dashboard
# Si aplica rebuild del panel:
docker compose build dashboard && docker compose up -d dashboard
```

- Usuario `admin` no se puede eliminar; siempre tiene todas las secciones.
- Tras migrar, los usuarios deben volver a iniciar sesión para refrescar permisos en el JWT.
----

psql -U $DB_USER -d $DB_NAME -f config-scripts/migrations/003_dashboard_users_permissions.sql
docker compose restart fastapi dashboard