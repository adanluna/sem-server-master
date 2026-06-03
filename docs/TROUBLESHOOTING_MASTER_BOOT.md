# Master — arranque tras reboot (`semefo-master.service`)

## Síntoma A — ningún contenedor tras reboot

`docker ps` vacío y:

```
semefo-master.service: Job ... failed with result 'dependency'.
```

Causa: `RequiresMountsFor=/mnt/wave` con **autofs/CIFS** — al boot el montaje aún no está activo y systemd aborta el servicio sin reintentar. Minutos después `/mnt/wave` sí responde.

**Recuperación inmediata** (con WAVE ya montado):

```bash
sudo systemctl start semefo-master
docker compose -f /opt/semefo/docker-compose.yml ps
```

Actualizar unit (sin `RequiresMountsFor`; el `ExecStartPre` ya espera hasta 60 s):

```bash
cd /opt/semefo
sudo cp deploy/semefo-master.service /etc/systemd/system/semefo-master.service
sudo systemctl daemon-reload
sudo systemctl enable semefo-master
```

## Síntoma B — solo 3 contenedores Up

Tras reiniciar el servidor solo suben 3 contenedores (`postgres`, `rabbitmq`, `fastapi`) y workers/dashboard quedan en `Created` o no arrancan.

`journalctl -u semefo-master -b` muestra:

```
error mounting "/mnt/wave" ... no such device
```

## Causa

`docker compose up -d` corre antes de que `/mnt/wave` (CIFS con `x-systemd.automount`) esté montado. Los workers necesitan bind-mount de `/mnt/wave`.

## Instalación / actualización del unit

```bash
cd /opt/semefo
sudo cp deploy/semefo-master.service /etc/systemd/system/semefo-master.service
sudo systemctl daemon-reload
sudo systemctl enable semefo-master
sudo systemctl reset-failed semefo-master
sudo systemctl start semefo-master
sudo systemctl status semefo-master
docker compose ps
```

Esperado: **6 contenedores Up**, servicio `active (exited)`.

## Verificación sin reboot

```bash
docker compose stop celery_uniones celery_manifest dashboard
sudo systemctl restart semefo-master
docker compose ps
```

## Requisitos previos

- `/etc/fstab` con montaje SMB a `/mnt/wave` (`_netdev`, idealmente accesible tras red)
- Docker habilitado al boot: `systemctl is-enabled docker`
- `/opt/semefo/storage/tmp` con permisos para UID 1000 (workers Celery)
