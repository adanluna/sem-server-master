## Infraestructura — grabador Hanwha en panel admin

El dashboard muestra tres nodos: **Master**, **Whisper** y **Grabador Hanwha** (ping + SMB 445 + montajes WAVE).

```bash
# Master: variables en .env
# GRABADOR_IP=172.21.82.4
# GRABADOR_SMB_PORT=445
# INFRA_CHECK_SMB_PORT=1
# WAVE_MOUNT=/mnt/wave
# EXPEDIENTES_PATH=/mnt/wave/archivos_sistema_semefo

docker compose up -d --build fastapi dashboard
```

- `GET /dashboard/infraestructura` incluye `grabador`, `grabador_status`, `wave_mount`.
- Tras desplegar: hard refresh en el navegador (Ctrl+Shift+R).

## Usuarios dashboard — admin visible y protegido

- `admin` aparece primero en la lista, con badge **protegido** y sin botón eliminar.
- Backend rechaza `DELETE` del usuario `admin` (403).

## Sesiones fallidas

- Solo listan sesiones con `payload_procesamiento` (reprocesables).
- Borre sesiones de prueba antiguas sin JSON; las nuevas desde la app ya guardan JSON.
- El Top 10 del dashboard puede mostrar errores viejos hasta que se limpien en BD.

```bash
docker compose up -d --build fastapi dashboard
```

## Arranque automático master (semefo-master.service)

Tras reboot, el stack debe levantar **6** contenedores. Si solo suben 3, actualizar la unidad systemd:

```bash
cd /opt/semefo
sudo cp deploy/semefo-master.service /etc/systemd/system/semefo-master.service
sudo systemctl daemon-reload
sudo systemctl enable semefo-master
sudo systemctl reset-failed semefo-master
sudo systemctl start semefo-master
docker compose ps
```

Detalle: `docs/TROUBLESHOOTING_MASTER_BOOT.md`

## Fix enum sesión — manifest / actualizar job 500

Si el worker manifest loguea `invalid input value for enum ... "procesado"` al completar un job:

```bash
cd /opt/semefo
docker compose exec -T db psql -U semefo_user -d semefo \
  < config-scripts/migrations/005_sesion_estado_enum_error.sql
docker compose up -d --build fastapi celery_manifest celery_uniones
```

- Migración `005`: añade `error` al enum de `sesiones.estado`.
- Código: ya no intenta guardar `procesado` (valor inválido); `finalizada` la marca el cierre de archivos.
- `api_server/utils/sesion_estado.py` valida estados antes de escribir en BD (`POST /sesiones/` y asignaciones internas).

## Dashboard — etapas de sesión más claras

- **Etapa** (UI): Creada (sin grabar), Grabando, Pausada, Grabada · sin procesar, En pipeline, Finalizada, Con error.
- **Estado BD**: valor técnico (`procesando`, `pausada`, `finalizada`, `error`).
- Lista **Sesiones abiertas recientes**: top 10 no finalizadas, **más nuevas primero** (antes: 10 más viejas).
- KPI **Abiertas** reemplaza el label confuso “Pendientes”.
- Tras rebuild: `docker compose up -d --build fastapi dashboard` (nginx con DNS dinámico a fastapi).

```bash
docker compose up -d --build fastapi dashboard
```

## App — sesiones: 1 usuario ↔ 1 tablet

- **Un usuario** solo puede tener **una sesión activa** (en una tablet). Si intenta entrar en otra → **409** informativo; debe cerrar sesión en la tablet donde está.
- **Una tablet** solo admite **un usuario** a la vez. Si otro usuario intenta entrar → **409** informativo; el usuario activo debe cerrar sesión en esa tablet.
- **Sin takeover:** no hay opción de cerrar sesión remota desde otra tablet.
- **Misma tablet, mismo usuario:** re-login y reabrir app permitidos; botón logout cierra en servidor.
- **JWT:** refresh fallido no borra tokens locales; logout forzado solo si admin revoca.

Rebuild APK + `docker compose up -d --build fastapi`.

Variables opcionales en `.env` master:
- `APP_SESSION_AUTO_CLOSE_IDLE=1` — reactivar cierre de sesiones idle abandonadas (no usado en operación normal).
- `APP_SESSION_STALE_MINUTES=30` — umbral si auto-close idle está activo.

## Infra — montaje Whisper (menos falsos negativos)

Whisper reporta montaje WAVE por **HTTP** (`POST /infra/whisper/mount`) además del JSON en share. El master **prioriza HTTP** y no confía en JSON OK si HTTP dejó de llegar.

```bash
# Master: migración + rebuild
cd /opt/semefo
docker compose exec -T db psql -U semefo_user -d semefo \
  < config-scripts/migrations/006_whisper_mount_reports.sql
docker compose up -d --build fastapi dashboard

# Whisper: git pull (healthcheck.py + api_client)
sudo systemctl restart whisper_listener
```

Variables opcionales master `.env`:
- `WHISPER_MOUNT_STALE_MINUTES=2` — antigüedad máxima reporte JSON (default 2).
- `WHISPER_MOUNT_HTTP_STALE_MINUTES=2` — antigüedad máxima reporte HTTP.

Whisper: `healthcheck.py` POST cada ~30 s (listener) + cron respaldo; log en `/opt/semefo/logs/infra.log`.

Dashboard infra: auto-refresh cada 45 s. App: `InfraMonitorService` cada 60 s con sesión activa.

## Dashboard — login 405 / no puede volver a entrar

- **Causa:** nginx enviaba `POST /api/dashboard/login` a FastAPI sin quitar `/api/`; el mount `app.mount("/api", api_app)` capturaba la ruta y el login admin (`POST /dashboard/login`) no se ejecutaba.
- **Fix:** `semefo-dashboard/nginx.conf` — `location ^~ /api/` + `proxy_pass http://fastapi:8000/` (sin variables; reescribe URI correctamente).

```bash
cd /opt/semefo
git pull
docker compose up -d --build dashboard
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8080/api/dashboard/login \
  -H "Content-Type: application/json" -d '{"username":"admin","password":"..."}'
# Debe responder 200
```

Si tras `docker compose up -d --build fastapi` el dashboard da **502**, ejecutar: `docker compose restart dashboard`.

Tras ~30 min el token dashboard expira; sin este fix el re-login fallaba con 405.

