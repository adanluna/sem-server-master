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
