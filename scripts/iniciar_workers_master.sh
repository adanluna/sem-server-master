#!/bin/bash
# ============================================================
# 🚀 Inicio del entorno SEMEFO - Server Master (Producción)
# Autor: Adan Luna
# Descripción:
#   Inicia, valida y muestra el estado de todos los contenedores
#   Docker del sistema SEMEFO (FastAPI, Celery, RabbitMQ, PostgreSQL)
# ============================================================

# --- Configuración ---
PROJECT_DIR="/opt/semefo"
LOG_DIR="$PROJECT_DIR/logs"
DATE=$(date +'%Y-%m-%d_%H-%M-%S')
LOGFILE="$LOG_DIR/iniciar_master_$DATE.log"

mkdir -p "$LOG_DIR"

echo "============================================================" | tee -a "$LOGFILE"
echo "🚀 Iniciando entorno SEMEFO - $(date +'%Y-%m-%d %H:%M:%S')" | tee -a "$LOGFILE"
echo "============================================================" | tee -a "$LOGFILE"

cd "$PROJECT_DIR" || { echo "❌ ERROR: No se encontró $PROJECT_DIR"; exit 1; }

# --- Verificar Docker Compose ---
if ! command -v docker-compose &> /dev/null; then
  echo "❌ ERROR: docker-compose no está instalado o no está en PATH." | tee -a "$LOGFILE"
  exit 1
fi

# --- Iniciar stack ---
echo "▶️ Levantando servicios con Docker Compose..." | tee -a "$LOGFILE"
docker-compose up -d --remove-orphans >> "$LOGFILE" 2>&1

if [ $? -ne 0 ]; then
  echo "❌ ERROR: Falló el inicio con docker-compose." | tee -a "$LOGFILE"
  exit 1
fi

# --- Verificar estado general ---
echo "" | tee -a "$LOGFILE"
echo "📋 Estado actual de contenedores:" | tee -a "$LOGFILE"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | tee -a "$LOGFILE"

# --- Verificar servicios esenciales ---
ESSENTIALS=("postgres_db" "rabbitmq" "celery_worker" "celery_video2" "fastapi_app")

for service in "${ESSENTIALS[@]}"; do
  if docker inspect --format '{{.State.Health.Status}}' "$service" 2>/dev/null | grep -q "healthy"; then
    echo "✅ $service: HEALTHY" | tee -a "$LOGFILE"
  else
    echo "⚠️  $service: no reporta 'healthy' (verificar logs)" | tee -a "$LOGFILE"
  fi
done

# --- Mostrar endpoints ---
echo "" | tee -a "$LOGFILE"
echo "🌐 Endpoints disponibles:" | tee -a "$LOGFILE"
echo "   ▶ API FastAPI:   http://192.168.1.11:8000/docs" | tee -a "$LOGFILE"
echo "   ▶ RabbitMQ UI:   http://192.168.1.11:15672" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

# --- Mostrar logs recientes ---
echo "🪵 Últimos eventos en logs de Celery:" | tee -a "$LOGFILE"
docker logs --tail 5 celery_worker 2>/dev/null | tee -a "$LOGFILE"

echo "" | tee -a "$LOGFILE"
echo "✅ SEMEFO Server Master iniciado correctamente." | tee -a "$LOGFILE"
echo "Log completo en: $LOGFILE"
echo "============================================================"