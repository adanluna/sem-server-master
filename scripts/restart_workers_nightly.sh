#!/bin/bash
# ============================================================
# Reinicio nocturno automático de Workers SEMEFO
# Este script se ejecuta por cron a las 03:00 am todos los días.
# No reinicia API ni base de datos.
# ============================================================

PROJECT_DIR="/opt/semefo"
SCRIPT_DIR="$PROJECT_DIR/scripts"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
LOGFILE="$LOG_DIR/restart_workers_$DATE.log"
PIDFILE="/tmp/semefo_restart_workers.pid"

mkdir -p "$LOG_DIR"

# ============================================================
# Prevención de ejecuciones simultáneas
# ============================================================
if [ -f "$PIDFILE" ]; then
    echo "Otro proceso de reinicio está en ejecución. Abortando." | tee -a "$LOGFILE"
    exit 1
fi

echo $$ > "$PIDFILE"

echo "============================================================" | tee -a "$LOGFILE"
echo "Reinicio nocturno de Workers SEMEFO - $(date)" | tee -a "$LOGFILE"
echo "============================================================" | tee -a "$LOGFILE"

# ============================================================
# Validación de scripts requeridos
# ============================================================
if [ ! -f "$SCRIPT_DIR/detener_workers_master.sh" ]; then
    echo "ERROR: No se encuentra detener_workers_master.sh" | tee -a "$LOGFILE"
    rm -f "$PIDFILE"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/iniciar_workers_master.sh" ]; then
    echo "ERROR: No se encuentra iniciar_workers_master.sh" | tee -a "$LOGFILE"
    rm -f "$PIDFILE"
    exit 1
fi

# ============================================================
# Detener workers
# ============================================================
echo "Deteniendo workers..." | tee -a "$LOGFILE"
bash "$SCRIPT_DIR/detener_workers_master.sh" >> "$LOGFILE" 2>&1
sleep 4

# ============================================================
# Iniciar workers
# ============================================================
echo "Iniciando workers..." | tee -a "$LOGFILE"
bash "$SCRIPT_DIR/iniciar_workers_master.sh" >> "$LOGFILE" 2>&1
sleep 3

# ============================================================
# Verificar estado de contenedores
# ============================================================
echo "Verificando estado de Celery workers..." | tee -a "$LOGFILE"

docker ps | grep celery | tee -a "$LOGFILE"

if ! docker ps | grep -q "celery_uniones"; then
    echo "ERROR: Worker celery_uniones NO está ejecutándose." | tee -a "$LOGFILE"
fi

if ! docker ps | grep -q "celery_manifest"; then
    echo "ADVERTENCIA: Worker celery_manifest no está activo (solo se usa en mantenimiento)." | tee -a "$LOGFILE"
fi

echo "Reinicio nocturno completado - $(date)" | tee -a "$LOGFILE"
echo "============================================================" | tee -a "$LOGFILE"

# Limpiar PID
rm -f "$PIDFILE"
exit 0
