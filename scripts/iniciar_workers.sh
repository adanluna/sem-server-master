#!/bin/bash
echo "🚀 Iniciando workers en tu Mac (fuera de Docker)..."

export DB_HOST=localhost
export RABBITMQ_URL=amqp://guest:guest@localhost:5672//

cd "$(dirname "$0")/.."
source venv/bin/activate

echo "✅ Variables temporales configuradas:"
echo "   DB_HOST=$DB_HOST"
echo "   RABBITMQ_URL=$RABBITMQ_URL"

echo "🐇 Worker transcripciones..."
celery -A worker.celery_app worker -Q transcripciones --loglevel=info -n worker_transcripciones@%h &

echo "🐇 Worker conversiones..."
celery -A worker.celery_app worker -Q conversiones_video --loglevel=info -n worker_conversiones@%h &

echo "🐇 Worker uniones..."
celery -A worker.celery_app worker -Q uniones_audio,uniones_video --loglevel=info -n worker_uniones@%h &

echo "✅ Todos los workers iniciados en background."
echo "Usa 'ps aux | grep celery' para verlos y 'scripts/detener_workers_mac.sh' para matarlos."
