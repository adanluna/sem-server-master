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
