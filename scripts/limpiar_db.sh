#!/bin/bash
# ============================================================
#  LIMPIEZA DE BASE DE DATOS SEMEFO (SOLO PARA PRUEBAS)
#  Autor: Adan Luna
#  Uso:
#      ./scripts/limpiar_db.sh
#      (desde cualquier directorio; usa .env y docker compose en /opt/semefo)
#
#  ATENCIÓN:
#   - NO borra usuarios, dispositivos ni transcripciones reales.
#   - Reinicia workers Celery para evitar inserciones durante el TRUNCATE.
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

echo "============================================================"
echo "   LIMPIEZA DE TABLAS DE PRUEBAS EN SEMEFO SOLO TEST"
echo "============================================================"

# --- Cargar variables de entorno (desde raíz del repo, no desde scripts/) ---
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
else
    echo "❌ ERROR: No se encontró .env en $PROJECT_ROOT"
    exit 1
fi

cd "$PROJECT_ROOT"

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
docker compose stop celery_uniones celery_manifest || true

echo ""
echo "🧹 Ejecutando TRUNCATE..."

docker exec -i postgres_db psql -U "$DB_USER" -d "$DB_NAME" <<EOF
TRUNCATE TABLE
    sesion_archivos,
    jobs,
    sesiones,
    investigaciones,
    logs_eventos,
    log_pausas
RESTART IDENTITY CASCADE;
EOF

echo ""
echo "✨ Tablas limpiadas correctamente:"
echo "   - sesion_archivos"
echo "   - jobs"
echo "   - sesiones"
echo "   - investigaciones"
echo "   - logs_eventos"
echo "   - log_pausas"

echo ""
echo "▶ Reiniciando workers..."
docker compose start celery_uniones celery_manifest

echo ""
echo "✅ Limpieza completada con éxito."
echo "============================================================"
