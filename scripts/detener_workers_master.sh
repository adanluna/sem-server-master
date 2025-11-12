#!/bin/bash
# ============================================================
# 🛑 Detener entorno SEMEFO - Server Master (Producción)
# Autor: Adan Luna
# Descripción:
#   Detiene todos los contenedores Docker del sistema SEMEFO
#   de forma segura y genera un log con el resultado.
# ============================================================

# --- Configuración ---
PROJECT_DIR="/opt/semefo"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
LOGFILE="$LOG_DIR/detener_master_$DATE.log"

mkdir -p "$LOG_DIR"

echo "============================================================" | tee -a "$LOGFILE"
echo "🛑 Deteniendo entorno SEMEFO - $(date +'%Y-%m-%d %H:%M:%S')" | tee -a "$LOGFILE"
echo "============================================================" | tee -a "$LOGFILE"

cd "$PROJECT_DIR" || { echo "❌ ERROR: No se encontró $PROJECT_DIR"; exit 1; }

# --- Verificar Docker Compose ---
if ! command -v docker-compose &> /dev/null; then
  echo "❌ ERROR: docker-compose no está instalado o no está en PATH." | tee -a "$LOGFILE"
  exit 1
fi

# --- Mostrar contenedores actuales ---
echo "📋 Contenedores activos antes de detener:" | tee -a "$LOGFILE"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | tee -a "$LOGFILE"

# --- Detener stack ---
echo "" | tee -a "$LOGFILE"
echo "▶️ Deteniendo servicios SEMEFO..." | tee -a "$LOGFILE"
docker-compose down >> "$LOGFILE" 2>&1

if [ $? -ne 0 ]; then
  echo "❌ ERROR: Falló el apagado con docker-compose." | tee -a "$LOGFILE"
  exit 1
fi

# --- Verificar estado ---
echo "" | tee -a "$LOGFILE"
echo "📋 Verificando contenedores después del apagado:" | tee -a "$LOGFILE"
docker ps --format "table {{.Names}}\t{{.Status}}" | tee -a "$LOGFILE"

# --- Confirmar ---
if [ "$(docker ps -q | wc -l)" -eq 0 ]; then
  echo "✅ Todos los contenedores SEMEFO se han detenido correctamente." | tee -a "$LOGFILE"
else
  echo "⚠️  Algunos contenedores siguen en ejecución. Revise manualmente con 'docker ps'." | tee -a "$LOGFILE"
fi

echo "" | tee -a "$LOGFILE"
echo "🪵 Log completo en: $LOGFILE" | tee -a "$LOGFILE"
echo "============================================================"
exit 0
