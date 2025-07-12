#!/bin/bash

# --- Configuración ---
# Nombre base del archivo de la aplicación Celery
CELERY_APP="worker.celery_app"
# Directorio base del proyecto (donde está el script 'iniciar_workers.sh')
PROJECT_ROOT="$(dirname "$0")/.."
# Directorio para los logs de Celery
LOG_DIR="${PROJECT_ROOT}/logs"

# --- Funciones Auxiliares ---
log_info() {
  echo "✅ INFO: $1"
}

log_action() {
  echo "🚀 ACCIÓN: $1"
}

log_error() {
  echo "❌ ERROR: $1" >&2
}

# --- Inicio del Script ---
log_action "Reiniciando workers Celery en tu Mac..."

# Matar procesos viejos de Celery de forma robusta
# Primero intenta una terminación elegante (TERM), espera un poco.
# Si persisten, usa una terminación forzosa (KILL).
echo "  > Deteniendo workers existentes (si los hay)..."
pkill -f "celery -A ${CELERY_APP}"
sleep 2 # Espera un poco para una terminación limpia

# Si aún hay procesos, mátalos forzosamente
if pgrep -f "celery -A ${CELERY_APP}" > /dev/null; then
  echo "  > Algunos workers persisten. Forzando detención..."
  pkill -9 -f "celery -A ${CELERY_APP}"
  sleep 1
fi

# Verificar si aún hay procesos (por si acaso)
if pgrep -f "celery -A ${CELERY_APP}" > /dev/null; then
  log_error "No se pudieron detener todos los workers existentes. Revise manualmente."
  exit 1
fi

# Crear directorio de logs si no existe
mkdir -p "${LOG_DIR}"

# Exportar variables de entorno (pueden ir en .env y cargarse con dotenv, por ejemplo)
export DB_HOST=localhost
export RABBITMQ_URL=amqp://guest:guest@localhost:5672//

log_info "Variables configuradas."

# Activar el entorno virtual
if [ -d "${PROJECT_ROOT}/venv" ]; then
  source "${PROJECT_ROOT}/venv/bin/activate"
  log_info "Entorno virtual activado."
else
  log_error "No se encontró el entorno virtual en '${PROJECT_ROOT}/venv'. Asegúrese de crearlo."
  exit 1
fi

# --- Iniciar Workers ---

# Worker transcripciones
log_action "Iniciando worker 'transcripciones' (concurrency=4)..."
nohup celery -A "${CELERY_APP}" worker -Q transcripciones --concurrency=4 --loglevel=info -n worker_transcripciones@%h > "${LOG_DIR}/worker_transcripciones.log" 2>&1 &
echo "  > PID: $!"

# Worker conversiones
log_action "Iniciando worker 'conversiones' (concurrency=2)..."
nohup celery -A "${CELERY_APP}" worker -Q conversiones_video --concurrency=2 --loglevel=info -n worker_conversiones@%h > "${LOG_DIR}/worker_conversiones.log" 2>&1 &
echo "  > PID: $!"

# Worker uniones
log_action "Iniciando worker 'uniones' (concurrency=2)..."
nohup celery -A "${CELERY_APP}" worker -Q uniones_audio,uniones_video --concurrency=2 --loglevel=info -n worker_uniones@%h > "${LOG_DIR}/worker_uniones.log" 2>&1 &
echo "  > PID: $!"

log_info "Todos los workers iniciados en background."
echo "---"

# Mostrar procesos actuales de Celery
log_info "Procesos actuales de Celery:"
ps aux | grep "[c]elery -A ${CELERY_APP}"

echo "---"
log_info "Script de inicio de workers completado."