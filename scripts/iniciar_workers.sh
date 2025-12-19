#!/bin/bash

# --- Configuración ---
CELERY_APP="worker.celery_app"
PROJECT_ROOT="$(dirname "$0")/.."
LOG_DIR="${PROJECT_ROOT}/logs"

log_info() {
  echo "✅ INFO: $1"
}

log_action() {
  echo "🚀 ACCIÓN: $1"
}

log_error() {
  echo "❌ ERROR: $1" >&2
}

# --- Inicio ---
log_action "Reiniciando workers Celery en tu Mac..."

echo "  > Deteniendo workers existentes..."
pkill -f "celery -A ${CELERY_APP}"
sleep 2

if pgrep -f "celery -A ${CELERY_APP}" > /dev/null; then
  echo "  > Algunos persisten. Forzando kill..."
  pkill -9 -f "celery -A ${CELERY_APP}"
  sleep 1
fi

if pgrep -f "celery -A ${CELERY_APP}" > /dev/null; then
  log_error "No se pudieron detener todos los workers. Revise manualmente."
  exit 1
fi

mkdir -p "${LOG_DIR}"

# --- Cargar variables desde .env ---
if [ -f "${PROJECT_ROOT}/.env" ]; then
  export $(grep -v '^#' "${PROJECT_ROOT}/.env" | xargs)
  log_info "Variables cargadas desde .env."
else
  log_error "No se encontró el archivo .env en ${PROJECT_ROOT}"
  exit 1
fi

# --- Activar venv ---
if [ -d "${PROJECT_ROOT}/venv" ]; then
  source "${PROJECT_ROOT}/venv/bin/activate"
  log_info "Entorno virtual activado."
else
  log_error "No se encontró el entorno virtual en '${PROJECT_ROOT}/venv'."
  exit 1
fi

# --- Iniciar workers ---
log_action "Iniciando 'uniones_video'..."
nohup celery -A "${CELERY_APP}" worker -Q uniones_video --concurrency=2 --loglevel=info -n worker_uniones_video@%h > "${LOG_DIR}/worker_uniones_video.log" 2>&1 &
echo "  > PID: $!"

log_action "Iniciando worker de Manifest..."
nohup celery -A "${CELERY_APP}" worker -Q manifest --loglevel=info \
  -n worker_manifest@%h >> "${LOG_DIR}/worker_manifest.log" 2>&1 &
echo "  > PID: $!"
