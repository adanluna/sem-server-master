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

## Health grabador Hanwha + montaje /mnt/wave

```bash
# Master: variables en .env (GRABADOR_IP, WAVE_MOUNT, EXPEDIENTES_PATH, GRABADOR_SMB_PORT)
docker compose restart fastapi dashboard celery_uniones celery_manifest

# Whisper: cron o systemd para healthcheck.py (escribe wave_mount_whisper.json)
# Ejemplo cada 2 min:
# */2 * * * * cd /opt/sem-server-whisper && .venv/bin/python healthcheck.py
sudo systemctl restart whisper-listener

# Rebuild app / dashboard si aplica
```

- `POST /infra/estado_general` incluye `grabador`, `wave_mount`, `infra_ok`.
- Panel Infraestructura muestra grabador y montajes master/whisper.
- App bloquea en login, expediente, grabar y botón en Config si falla grabador o mount.
- Si cambian password SMB del grabador: actualizar `.env` + `montaje_smb.sh` / fstab y remontar en master y whisper.
----

## Sesiones app LDAP (un login por tablet)

```bash
psql -U $DB_USER -d $DB_NAME -f config-scripts/migrations/004_app_user_sessions.sql
docker compose restart fastapi dashboard
# Rebuild app Flutter / dashboard si aplica
```

Variables en `.env`:
- `APP_SESSION_STALE_MINUTES=30` — sin heartbeat → cierre automático
- `APP_SESSION_HEARTBEAT_INTERVAL_SEC=45` — referencia para la app

Comportamiento:
- Un operador LDAP = una sesión app activa (`app_user_sessions`).
- Heartbeat cada ~45 s (también en pausa local de grabación).
- Login en otra tablet: **bloqueado** si `recording`; **takeover** con confirmación si idle.
- Logout operador: pausa sesión forense en servidor + revoca tokens.
- Panel **Sesiones app** (`/sesiones-app`, permiso `sesiones`): listar y cerrar remotamente (403 si grabando).

----
docker compose restart fastapi dashboard celery_uniones celery_manifest
# Whisper: healthcheck periódico + reinicio listener si aplica

----
# Master
psql -U $DB_USER -d $DB_NAME -f config-scripts/migrations/004_app_user_sessions.sql
docker compose restart fastapi dashboard
docker compose build dashboard && docker compose up -d dashboard   # si aplica

# App tablet: rebuild e instalar APK