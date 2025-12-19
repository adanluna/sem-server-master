#!/bin/bash
# ============================================================
# Detener workers Celery del sistema SEMEFO (Server Master)
# Solo detiene workers: no toca API, RabbitMQ ni Postgres.
# ============================================================

PROJECT_DIR="/opt/semefo"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
LOGFILE="$LOG_DIR/detener_workers_$DATE.log"

mkdir -p "$LOG_DIR"

echo "============================================================" | tee -a "$LOGFILE"
echo "Deteniendo workers SEMEFO - $(date)" | tee -a "$LOGFILE"
echo "============================================================" | tee -a "$LOGFILE"

cd "$PROJECT_DIR" || {
    echo "ERROR: No se encontró $PROJECT_DIR" | tee -a "$LOGFILE"
    exit 1
}

# Lista de workers a detener
WORKERS=(
    "celery_uniones"
    "celery_manifest"
)

echo "Deteniendo contenedores de workers..." | tee -a "$LOGFILE"

for worker in "${WORKERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "$worker"; then
        echo "Deteniendo $worker..." | tee -a "$LOGFILE"
        docker stop "$worker" >> "$LOGFILE" 2>&1
    else
        echo "$worker no está en ejecución." | tee -a "$LOGFILE"
    fi
done

echo "" | tee -a "$LOGFILE"
echo "Estado final de contenedores:" | tee -a "$LOGFILE"
docker ps --format "table {{.Names}}\t{{.Status}}" | tee -a "$LOGFILE"

echo "Workers detenidos correctamente." | tee -a "$LOGFILE"
echo "============================================================"
exit 0
