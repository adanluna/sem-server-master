#!/bin/bash
echo "🛑 Deteniendo contenedores actuales..."
docker-compose down
docker-compose build --no-cache 

echo "🚀 Reconstruyendo imágenes (sin tocar volúmenes)..."
docker-compose up --build -d

echo "✅ Docker rebuild completo. Contenedores levantados en background."
echo "📦 Usa 'docker-compose ps' para ver su estado."
