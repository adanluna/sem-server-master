#!/bin/bash
# ============================================================
# 🌙 Reinicio nocturno automático de Workers SEMEFO
# Fecha: $(date)
# ============================================================

PROJECT_DIR="/opt/semefo"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
LOGFILE="$LOG_DIR/restart_workers_$DATE.log"

mkdir -p "$LOG_DIR"

echo "============================================================" | tee -a "$LOGFILE"
echo "🌙 Reinicio nocturno de Workers SEMEFO - $(date)" | tee -a "$LOGFILE"
echo "============================================================" | tee -a "$LOGFILE"

# Detener workers (sin apagar DB ni API)
bash "$PROJECT_DIR/scripts/detener_workers_master.sh" >> "$LOGFILE" 2>&1
sleep 5

# Iniciar workers nuevamente
bash "$PROJECT_DIR/scripts/iniciar_workers_master.sh" >> "$LOGFILE" 2>&1

echo "" | tee -a "$LOGFILE"
echo "✅ Reinicio de workers completado - $(date)" | tee -a "$LOGFILE"
echo "============================================================"
exit 0
