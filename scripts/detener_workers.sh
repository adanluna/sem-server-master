#!/bin/bash

echo "🛑 Buscando y deteniendo todos los workers Celery..."

# Usar pkill para buscar cualquier proceso celery
pkill -f 'celery'

if [ $? -eq 0 ]; then
    echo "✅ Todos los workers Celery detenidos correctamente."
else
    echo "⚠️ No se encontraron procesos Celery activos o ocurrió un error."
fi
