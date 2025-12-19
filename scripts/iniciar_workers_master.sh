#!/bin/bash
# ============================================================
# Iniciar workers Celery del sistema SEMEFO (Server Master)
# No inicia API, RabbitMQ ni Postgres: solo workers.
# ============================================================

PROJECT_DIR="/opt/semefo"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
LOGFILE="$LOG_DIR/iniciar_workers_$DATE.log"

mkdir -p "$LOG_DIR"

echo "============================================================" | tee -a "$LOGFILE"
echo "Iniciando workers SEMEFO - $(date)" | tee -a "$LOGFILE"
echo "============================================================" | tee -a "$LOGFILE"

cd "$PROJECT_DIR" || {
    echo "ERROR: No se encontró $PROJECT_DIR" | tee -a "$LOGFILE"
    exit 1
}

# Iniciar workers específicos (sin romper otros servicios)
echo "Levantando workers Celery..." | tee -a "$LOGFILE"

docker compose up -d celery_uniones     >> "$LOGFILE" 2>&1
docker compose up -d celery_manifest    >> "$LOGFILE" 2>&1

sleep 3

echo "" | tee -a "$LOGFILE"
echo "Verificando estado de workers..." | tee -a "$LOGFILE"

for worker in celery_uniones celery_manifest; do
    if docker ps --format '{{.Names}}' | grep -q "$worker"; then
        echo "$worker iniciado correctamente." | tee -a "$LOGFILE"
    else
        echo "ERROR: $worker NO está en ejecución." | tee -a "$LOGFILE"
    fi
done

echo "" | tee -a "$LOGFILE"
echo "Estado actual de contenedores:" | tee -a "$LOGFILE"
docker ps --format "table {{.Names}}\t{{.Status}}" | tee -a "$LOGFILE"

echo "Workers iniciados correctamente." | tee -a "$LOGFILE"
echo "============================================================"
exit 0
