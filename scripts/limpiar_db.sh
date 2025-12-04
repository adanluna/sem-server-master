#!/bin/bash
# ============================================================
#  LIMPIEZA DE BASE DE DATOS SEMEFO (SOLO PARA PRUEBAS)
#  Autor: Adan Luna
#  Uso:
#      ./scripts/limpiar_db_pruebas.sh
#
#  ATENCIÓN:
#   - NO borra usuarios, dispositivos ni transcripciones reales.
#   - Reinicia workers Celery para evitar inserciones durante el TRUNCATE.
# ============================================================

set -e

echo "============================================================"
echo "   LIMPIEZA DE TABLAS DE PRUEBAS EN SEMEFO"
echo "============================================================"

# --- Cargar variables de entorno ---
if [ -f ".env" ]; then
    source .env
else
    echo "❌ ERROR: No se encontró .env en el directorio actual."
    exit 1
fi

echo "📌 Base de datos: $DB_NAME"
echo "📌 Usuario: $DB_USER"
echo "📌 Host: $DB_HOST"
echo ""

read -p "¿Seguro que deseas limpiar las tablas de pruebas? (si/no): " CONFIRM

if [ "$CONFIRM" != "si" ]; then
    echo "❌ Operación cancelada."
    exit 0
fi

echo ""
echo "🚫 Deteniendo Celery workers para evitar escritura durante limpieza..."
docker compose stop celery_uniones celery_video2 celery_manifest || true

echo ""
echo "🧹 Ejecutando TRUNCATE..."

docker exec -i postgres_db psql -U "$DB_USER" -d "$DB_NAME" <<EOF
TRUNCATE TABLE
    sesion_archivos,
    jobs,
    sesiones,
    investigaciones,
    logs_eventos
RESTART IDENTITY CASCADE;
EOF

echo ""
echo "✨ Tablas limpiadas correctamente:"
echo "   - sesion_archivos"
echo "   - jobs"
echo "   - sesiones"
echo "   - investigaciones"
echo "   - logs_eventos"

echo ""
echo "▶ Reiniciando workers..."
docker compose start celery_uniones celery_video2 celery_manifest

echo ""
echo "✅ Limpieza completada con éxito."
echo "============================================================"
